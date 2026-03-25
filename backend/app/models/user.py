"""User model — subscription tier, coach persona, timezone, quiet hours, push token."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    apple_user_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    subscription_tier: Mapped[str] = mapped_column(String(20), default="paid")  # v0.1: paid only
    coach_persona: Mapped[str | None] = mapped_column(String(2000), nullable=True)  # v0.2
    timezone: Mapped[str] = mapped_column(String(50), default="America/New_York")
    quiet_hours: Mapped[str | None] = mapped_column(String(20), nullable=True, default="22:00-07:00")
    push_token: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    thresholds = relationship("Threshold", back_populates="user", cascade="all, delete-orphan")
    metric_logs = relationship("MetricLog", back_populates="user", cascade="all, delete-orphan")
