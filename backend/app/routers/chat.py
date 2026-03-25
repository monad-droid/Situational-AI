"""Active coaching chat — Claude Haiku 4.5 for multi-turn conversations.

Daily message limit: 10 messages/day per user (v0.1).
This is the selling point — the coach isn't a one-way nag, it's a conversation.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models.chat_session import ChatMessage, ChatSession
from backend.app.models.threshold import Threshold
from backend.app.routers.auth import get_current_user
from backend.app.services.coaching_provider import get_chat_provider
from backend.app.services.system_prompt import COACHING_SYSTEM_PROMPT, build_user_context
from backend.app.services.threshold_engine import (
    get_days_over_threshold,
    get_latest_value,
    get_recent_history,
    get_trend_summary,
)

router = APIRouter(prefix="/api", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None  # Omit to start new session


class ChatResponse(BaseModel):
    response: str
    session_id: str
    messages_remaining_today: int


@router.post("/chat", response_model=ChatResponse)
async def coaching_chat(
    request: ChatRequest,
    authorization: str = Header(""),
    db: AsyncSession = Depends(get_db),
):
    """Send a message to the coaching AI and get a response.

    Uses Claude Haiku 4.5 for higher quality multi-turn conversation.
    Daily limit: 10 messages per user.
    """
    user = await get_current_user(authorization, db)

    # Rate limit: count messages sent today
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.count(ChatMessage.id))
        .join(ChatSession)
        .where(
            ChatSession.user_id == user.id,
            ChatMessage.role == "user",
            ChatMessage.created_at >= today_start,
        )
    )
    messages_today = result.scalar() or 0

    if messages_today >= settings.daily_chat_message_limit:
        raise HTTPException(
            status_code=429,
            detail=f"Daily chat limit reached ({settings.daily_chat_message_limit} messages). Try again tomorrow.",
        )

    # Get or create session
    if request.session_id:
        sess_result = await db.execute(
            select(ChatSession).where(
                ChatSession.id == uuid.UUID(request.session_id),
                ChatSession.user_id == user.id,
            )
        )
        session = sess_result.scalar_one_or_none()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        session = ChatSession(user_id=user.id)
        db.add(session)
        await db.flush()

    # Save user message
    user_msg = ChatMessage(
        session_id=session.id,
        role="user",
        content=request.message,
    )
    db.add(user_msg)
    session.message_count += 1

    # Build context from active threshold
    thresh_result = await db.execute(
        select(Threshold).where(Threshold.user_id == user.id, Threshold.is_active == True).limit(1)
    )
    threshold = thresh_result.scalar_one_or_none()

    user_context = ""
    if threshold:
        current_value = await get_latest_value(user.id, threshold.metric_type, db)
        if current_value is not None:
            days_count = await get_days_over_threshold(threshold, db)
            trend = await get_trend_summary(threshold, db)
            history = await get_recent_history(threshold, db)
            user_context = build_user_context(
                current_value=current_value,
                unit=threshold.unit,
                threshold_value=threshold.target_value,
                direction=threshold.direction,
                days_count=days_count,
                trend_summary=trend,
                recent_history=history,
                persona_override=user.coach_persona or "",
            )

    # Load conversation history for this session
    msgs_result = await db.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at)
    )
    all_messages = msgs_result.scalars().all()
    conversation = [{"role": m.role, "content": m.content} for m in all_messages]

    # Generate response via Claude Haiku 4.5
    provider = get_chat_provider()
    try:
        response_text = await provider.generate_chat_response(
            COACHING_SYSTEM_PROMPT, user_context, conversation
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI provider error: {str(e)}")

    # Save assistant message
    assistant_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=response_text,
        model_used=settings.chat_model,
    )
    db.add(assistant_msg)
    session.message_count += 1
    await db.commit()

    remaining = settings.daily_chat_message_limit - messages_today - 1

    return ChatResponse(
        response=response_text,
        session_id=str(session.id),
        messages_remaining_today=max(remaining, 0),
    )
