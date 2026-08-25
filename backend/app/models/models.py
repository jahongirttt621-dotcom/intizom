from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class User(Base):
    """Telegram foydalanuvchisi."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Ro'yxatdan o'tish ma'lumotlari
    full_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Holat: "new" (hali ariza bermagan), "pending" (kutmoqda),
    #        "approved" (tasdiqlangan), "rejected" (rad etilgan)
    status: Mapped[str] = mapped_column(String(16), default="new", index=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    participations: Mapped[list["Participation"]] = relationship(back_populates="user")


class Challenge(Base):
    """Ommaviy raqobat (challenge)."""

    __tablename__ = "challenges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(128))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    emoji: Mapped[str] = mapped_column(String(8), default="🔥")
    # Necha kunlik challenge (masalan 30)
    duration_days: Mapped[int] = mapped_column(Integer, default=30)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    participations: Mapped[list["Participation"]] = relationship(back_populates="challenge")


class Participation(Base):
    """Foydalanuvchining bitta challenge'dagi ishtiroki va streak holati."""

    __tablename__ = "participations"
    __table_args__ = (UniqueConstraint("user_id", "challenge_id", name="uq_user_challenge"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    challenge_id: Mapped[int] = mapped_column(ForeignKey("challenges.id", ondelete="CASCADE"), index=True)

    current_streak: Mapped[int] = mapped_column(Integer, default=0)
    best_streak: Mapped[int] = mapped_column(Integer, default=0)
    total_checkins: Mapped[int] = mapped_column(Integer, default=0)
    # Reyting balli: streak + total asosida hisoblanadi
    points: Mapped[int] = mapped_column(Integer, default=0, index=True)
    last_checkin_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="participations")
    challenge: Mapped["Challenge"] = relationship(back_populates="participations")
    checkins: Mapped[list["CheckIn"]] = relationship(back_populates="participation")


class CheckIn(Base):
    """Bitta kunlik tasdiq (check-in)."""

    __tablename__ = "checkins"
    __table_args__ = (UniqueConstraint("participation_id", "checkin_date", name="uq_participation_date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    participation_id: Mapped[int] = mapped_column(ForeignKey("participations.id", ondelete="CASCADE"), index=True)
    checkin_date: Mapped[date] = mapped_column(Date)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    participation: Mapped["Participation"] = relationship(back_populates="checkins")
