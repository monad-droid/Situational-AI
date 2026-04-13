"""CoachingMessage — nudges and chat responses.

Messages can be:
- Sent immediately (outside quiet hours)
- Queued for later (during quiet hours) — content is null until generation at send time
- Discarded (queued but user went back under threshold before delivery)
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.database import Base


class CoachingMessage(Base):
    __tablename__ = "coaching_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    threshold_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("thresholds.id"))
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    trigger_context: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    model_used: Mapped[str | None] = mapped_column(String(50), nullable=True)
    message_type: Mapped[str] = mapped_column(String(20), default="nudge")  # "nudge" | "chat_response"
    status: Mapped[str] = mapped_column(String(20), default="queued")  # "queued" | "sent" | "failed" | "discarded"
    scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
