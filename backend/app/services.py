"""Asosiy biznes-logika: foydalanuvchi, check-in, streak, reyting."""

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.models import Challenge, CheckIn, Participation, User

_TZ = ZoneInfo(settings.TIMEZONE)


def today() -> date:
    """Sozlangan vaqt mintaqasidagi bugungi sana."""
    return datetime.now(_TZ).date()


def _calc_points(current_streak: int, total_checkins: int, best_streak: int) -> int:
    """
    Reyting balli.
    Formula: joriy streak og'irroq (motivatsiya), best_streak va total ham hissa qo'shadi.
    """
    return current_streak * 10 + best_streak * 3 + total_checkins * 2


def _checkin_window_open() -> bool:
    """Agar vaqt oynasi sozlangan bo'lsa, hozir check-in qilish mumkinmi tekshiradi."""
    start = settings.CHECKIN_START_HOUR
    end = settings.CHECKIN_END_HOUR
    if start is None or end is None:
        return True
    now_hour = datetime.now(_TZ).hour
    if start <= end:
        return start <= now_hour < end
    # tun orqali o'tuvchi oyna (masalan 22 -> 06)
    return now_hour >= start or now_hour < end


async def get_or_create_user(session: AsyncSession, tg_user: dict) -> User:
    """Telegram ma'lumoti asosida foydalanuvchini topadi yoki yaratadi."""
    telegram_id = tg_user["id"]
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            telegram_id=telegram_id,
            username=tg_user.get("username"),
            first_name=tg_user.get("first_name"),
            photo_url=tg_user.get("photo_url"),
        )
        session.add(user)
        await session.flush()
    else:
        # profil ma'lumotini yangilab turamiz
        user.username = tg_user.get("username") or user.username
        user.first_name = tg_user.get("first_name") or user.first_name
        user.photo_url = tg_user.get("photo_url") or user.photo_url

    await session.commit()
    await session.refresh(user)
    return user


async def list_challenges(session: AsyncSession) -> list[Challenge]:
    result = await session.execute(
        select(Challenge).where(Challenge.is_active == True).order_by(Challenge.created_at)  # noqa: E712
    )
    return list(result.scalars().all())


async def join_challenge(session: AsyncSession, user: User, challenge_id: int) -> Participation:
    """Foydalanuvchini challenge'ga qo'shadi (yoki mavjud ishtirokni qaytaradi)."""
    result = await session.execute(
        select(Participation).where(
            Participation.user_id == user.id, Participation.challenge_id == challenge_id
        )
    )
    part = result.scalar_one_or_none()
    if part:
        return part

    # challenge mavjudligini tekshirish
    ch = await session.get(Challenge, challenge_id)
    if ch is None or not ch.is_active:
        raise ValueError("Challenge topilmadi yoki faol emas")

    part = Participation(user_id=user.id, challenge_id=challenge_id)
    session.add(part)
    await session.commit()
    await session.refresh(part)
    return part


async def do_checkin(session: AsyncSession, user: User, challenge_id: int, note: str | None = None) -> dict:
    """
    Bugungi check-in'ni ro'yxatga oladi va streak'ni yangilaydi.

    Qaytaradi: {status, current_streak, points, message}
    """
    if not _checkin_window_open():
        return {"status": "closed", "message": "Hozir check-in vaqti emas"}

    result = await session.execute(
        select(Participation).where(
            Participation.user_id == user.id, Participation.challenge_id == challenge_id
        )
    )
    part = result.scalar_one_or_none()
    if part is None:
        # avtomatik qo'shilib checkin qilamiz
        part = await join_challenge(session, user, challenge_id)

    d = today()

    # bugun allaqachon qilinganmi?
    existing = await session.execute(
        select(CheckIn).where(CheckIn.participation_id == part.id, CheckIn.checkin_date == d)
    )
    if existing.scalar_one_or_none():
        return {
            "status": "already",
            "current_streak": part.current_streak,
            "points": part.points,
            "message": "Bugun allaqachon belgilagansiz ✅",
        }

    # streak hisoblash
    if part.last_checkin_date == d - timedelta(days=1):
        part.current_streak += 1
    else:
        part.current_streak = 1  # uzilgan yoki birinchi marta

    part.best_streak = max(part.best_streak, part.current_streak)
    part.total_checkins += 1
    part.last_checkin_date = d
    part.points = _calc_points(part.current_streak, part.total_checkins, part.best_streak)

    session.add(CheckIn(participation_id=part.id, checkin_date=d, note=note))
    await session.commit()
    await session.refresh(part)

    return {
        "status": "ok",
        "current_streak": part.current_streak,
        "best_streak": part.best_streak,
        "points": part.points,
        "message": f"Zo'r! {part.current_streak} kunlik streak 🔥",
    }


async def reset_broken_streaks(session: AsyncSession) -> int:
    """
    Kun o'tkazib yuborganlarning streak'ini nolga tushiradi.
    Scheduler orqali har kuni ishga tushadi. Qaytaradi: nechta streak uzildi.
    """
    d = today()
    yesterday = d - timedelta(days=1)

    result = await session.execute(
        select(Participation).where(
            Participation.current_streak > 0,
            (Participation.last_checkin_date < yesterday) | (Participation.last_checkin_date.is_(None)),
        )
    )
    broken = list(result.scalars().all())
    for part in broken:
        part.current_streak = 0
        part.points = _calc_points(0, part.total_checkins, part.best_streak)

    if broken:
        await session.commit()
    return len(broken)


async def get_leaderboard(session: AsyncSession, challenge_id: int, limit: int = 50) -> list[dict]:
    """Challenge bo'yicha ommaviy reyting (points bo'yicha kamayish tartibida)."""
    result = await session.execute(
        select(Participation, User)
        .join(User, Participation.user_id == User.id)
        .where(Participation.challenge_id == challenge_id)
        .order_by(desc(Participation.points), desc(Participation.current_streak))
        .limit(limit)
    )
    rows = result.all()
    board = []
    for rank, (part, user) in enumerate(rows, start=1):
        board.append(
            {
                "rank": rank,
                "telegram_id": user.telegram_id,
                "name": user.first_name or user.username or "Anonim",
                "username": user.username,
                "photo_url": user.photo_url,
                "current_streak": part.current_streak,
                "best_streak": part.best_streak,
                "total_checkins": part.total_checkins,
                "points": part.points,
            }
        )
    return board


async def get_user_stats(session: AsyncSession, user: User) -> dict:
    """Foydalanuvchining barcha challenge'lardagi holati + umumiy o'rni."""
    result = await session.execute(
        select(Participation, Challenge)
        .join(Challenge, Participation.challenge_id == Challenge.id)
        .where(Participation.user_id == user.id)
    )
    rows = result.all()
    participations = []
    checked_today = False
    d = today()

    for part, ch in rows:
        is_today = part.last_checkin_date == d
        checked_today = checked_today or is_today
        participations.append(
            {
                "challenge_id": ch.id,
                "challenge_title": ch.title,
                "emoji": ch.emoji,
                "current_streak": part.current_streak,
                "best_streak": part.best_streak,
                "total_checkins": part.total_checkins,
                "points": part.points,
                "checked_today": is_today,
            }
        )

    total_points = sum(p["points"] for p in participations)
    return {
        "user": {
            "telegram_id": user.telegram_id,
            "name": user.first_name or user.username or "Anonim",
            "photo_url": user.photo_url,
        },
        "total_points": total_points,
        "participations": participations,
    }


async def seed_default_challenges(session: AsyncSession) -> None:
    """Agar hech qanday challenge bo'lmasa, boshlang'ich namunalarni qo'shadi."""
    count = await session.scalar(select(func.count()).select_from(Challenge))
    if count and count > 0:
        return

    defaults = [
        Challenge(title="Erta turish", description="Har kuni 06:00 gacha turish", emoji="🌅", duration_days=30),
        Challenge(title="Sport", description="Har kuni kamida 20 daqiqa mashq", emoji="💪", duration_days=30),
        Challenge(title="Kitob o'qish", description="Har kuni 10 bet", emoji="📚", duration_days=30),
        Challenge(title="Suv ichish", description="Kuniga 2 litr suv", emoji="💧", duration_days=21),
    ]
    session.add_all(defaults)
    await session.commit()
