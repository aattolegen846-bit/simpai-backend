from datetime import datetime, timezone
from sqlalchemy import Integer, String, JSON, ForeignKey, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import db

class Referral(db.Model):
    __tablename__ = "referrals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    referrer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    referee_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=True)
    code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)
    redeemed: Mapped[bool] = mapped_column(default=False)

class UserEvent(db.Model):
    __tablename__ = "user_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    data: Mapped[dict] = mapped_column(JSON, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

class Subscription(db.Model):
    __tablename__ = "subscriptions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    plan_id: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc))

class UserSkill(db.Model):
    __tablename__ = "user_skills"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    skill: Mapped[str] = mapped_column(String(64), nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
