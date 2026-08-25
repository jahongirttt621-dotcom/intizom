"""Mini App frontend uchun REST API endpointlari."""

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app import services
from app.auth import validate_init_data
from app.config import settings
from app.database import get_session

router = APIRouter(prefix="/api", tags=["api"])


async def get_current_user(
    x_init_data: str = Header(..., alias="X-Init-Data"),
    session: AsyncSession = Depends(get_session),
):
    """
    Har protected endpoint uchun dependency.
    Frontend `X-Init-Data` headerda Telegram initData yuboradi.
    """
    try:
        tg_user = validate_init_data(x_init_data)
    except ValueError as e:
        raise HTTPException(status_code=401, detail=f"Auth xato: {e}")

    return await services.get_or_create_user(session, tg_user)


async def require_approved(user=Depends(get_current_user)):
    """Faqat tasdiqlangan foydalanuvchilar uchun."""
    if user.status != "approved":
        raise HTTPException(status_code=403, detail="Ruxsat yo'q — admin tasdig'i kerak")
    return user


async def require_admin(user=Depends(get_current_user)):
    """Faqat admin uchun."""
    if user.telegram_id != settings.ADMIN_ID:
        raise HTTPException(status_code=403, detail="Faqat admin uchun")
    return user


# ---------- Schemas ----------
class RegisterRequest(BaseModel):
    full_name: str
    phone: str


class ModerateRequest(BaseModel):
    user_id: int
    action: str  # "approve" yoki "reject"


class JoinRequest(BaseModel):
    challenge_id: int


class CheckInRequest(BaseModel):
    challenge_id: int
    note: str | None = None


# ---------- Endpoints ----------
@router.get("/me")
async def me(user=Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    return await services.get_user_stats(session, user)


@router.post("/register")
async def register(
    body: RegisterRequest, user=Depends(get_current_user), session: AsyncSession = Depends(get_session)
):
    if not body.full_name.strip() or not body.phone.strip():
        raise HTTPException(status_code=400, detail="Ism va telefon to'ldirilishi shart")
    u = await services.register_user(session, user, body.full_name, body.phone)
    return {"status": u.status}


@router.get("/challenges")
async def challenges(user=Depends(require_approved), session: AsyncSession = Depends(get_session)):
    items = await services.list_challenges(session)
    return [
        {
            "id": c.id,
            "title": c.title,
            "description": c.description,
            "emoji": c.emoji,
            "duration_days": c.duration_days,
        }
        for c in items
    ]


@router.post("/join")
async def join(
    body: JoinRequest, user=Depends(require_approved), session: AsyncSession = Depends(get_session)
):
    try:
        part = await services.join_challenge(session, user, body.challenge_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "ok", "participation_id": part.id}


@router.post("/checkin")
async def checkin(
    body: CheckInRequest, user=Depends(require_approved), session: AsyncSession = Depends(get_session)
):
    return await services.do_checkin(session, user, body.challenge_id, body.note)


@router.get("/leaderboard/{challenge_id}")
async def leaderboard(
    challenge_id: int, user=Depends(require_approved), session: AsyncSession = Depends(get_session)
):
    board = await services.get_leaderboard(session, challenge_id)
    for row in board:
        row["is_me"] = row["telegram_id"] == user.telegram_id
    return board


# ---------- Admin ----------
@router.get("/admin/pending")
async def admin_pending(user=Depends(require_admin), session: AsyncSession = Depends(get_session)):
    return await services.list_pending_users(session)


@router.post("/admin/moderate")
async def admin_moderate(
    body: ModerateRequest, user=Depends(require_admin), session: AsyncSession = Depends(get_session)
):
    status = "approved" if body.action == "approve" else "rejected"
    u = await services.set_user_status(session, body.user_id, status)
    if u is None:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi")
    return {"status": u.status, "user_id": u.id}
