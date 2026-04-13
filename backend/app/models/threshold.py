"""Threshold model — defines when the coach activates.

v0.1: One threshold per user, body weight only.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Double, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class Threshold(Base):
    __tablename__ = "thresholds"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    metric_type: Mapped[str] = mapped_column(String(50), default="bodyMass")
    target_value: Mapped[float] = mapped_column(Double)
    direction: Mapped[str] = mapped_column(String(10), default="above")  # "above" | "below"
    unit: Mapped[str] = mapped_column(String(10), default="lb")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_nudge_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="thresholds")
