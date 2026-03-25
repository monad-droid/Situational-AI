"""MetricLog — stores health samples from HealthKit or manual entry.

Deduplication: HealthKit can deliver batched/duplicate samples. We use
(user_id, metric_type, recorded_at, value) as a uniqueness constraint.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Double, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.database import Base


class MetricLog(Base):
    __tablename__ = "metric_logs"
    __table_args__ = (
        UniqueConstraint("user_id", "metric_type", "recorded_at", "value", name="uq_metric_sample"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    metric_type: Mapped[str] = mapped_column(String(50))
    value: Mapped[float] = mapped_column(Double)
    unit: Mapped[str] = mapped_column(String(10))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(String(20), default="healthkit")  # "healthkit" | "manual"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="metric_logs")
