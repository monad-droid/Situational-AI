"""Nudge orchestration — the core flow that ties everything together.

When new samples arrive:
1. Evaluate thresholds (deterministic — no LLM)
2. Check idempotency (was a nudge already sent for this threshold window?)
3. Check quiet hours
4. Generate coaching message (GPT-5 Mini)
5. Send push notification (APNs with collapse-id)

This is the single entry point for the threshold-check → nudge pipeline.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.models.coaching_message import CoachingMessage
from backend.app.models.threshold import Threshold
from backend.app.models.user import User
from backend.app.services.coaching_provider import get_nudge_provider
from backend.app.services.push_service import send_push_notification
from backend.app.services.quiet_hours import get_quiet_hours_end, is_in_quiet_hours
from backend.app.services.system_prompt import COACHING_SYSTEM_PROMPT, build_user_context
from backend.app.services.threshold_engine import (
    get_days_over_threshold,
    get_recent_history,
    get_trend_summary,
    is_threshold_breached,
)

logger = logging.getLogger(__name__)


async def process_threshold_check(user: User, threshold: Threshold, db: AsyncSession) -> None:
    """Full nudge pipeline for a single threshold. Called after new samples are ingested."""

    # 1. Deterministic threshold evaluation — no LLM
    breached = await is_threshold_breached(threshold, db)
    if not breached:
        return

    # 2. Idempotency — don't spam
    if not await _should_send_nudge(threshold):
        return

    # 3. Build context for the AI
    days_count = await get_days_over_threshold(threshold, db)
    trend = await get_trend_summary(threshold, db)
    history = await get_recent_history(threshold, db)

    from backend.app.services.threshold_engine import get_latest_value
    current_value = await get_latest_value(user.id, threshold.metric_type, db)

    from backend.app.routers.subscriptions import COACH_PERSONAS
    persona_text = COACH_PERSONAS.get(user.coach_persona or "", user.coach_persona or "")

    user_context = build_user_context(
        current_value=current_value,
        unit=threshold.unit,
        threshold_value=threshold.target_value,
        direction=threshold.direction,
        days_count=days_count,
        trend_summary=trend,
        recent_history=history,
        persona_override=persona_text,
    )

    trigger_context = {
        "current_value": current_value,
        "unit": threshold.unit,
        "threshold_value": threshold.target_value,
        "direction": threshold.direction,
        "days_count": days_count,
        "trend_summary": trend,
        "recent_history": history,
    }

    # 4. Check quiet hours
    if is_in_quiet_hours(user.timezone, user.quiet_hours):
        scheduled_for = get_quiet_hours_end(user.timezone, user.quiet_hours)
        # Queue for later — do NOT generate content yet (it'll be stale by morning)
        msg = CoachingMessage(
            user_id=user.id,
            threshold_id=threshold.id,
            content=None,
            trigger_context=trigger_context,
            model_used=None,
            message_type="nudge",
            status="queued",
            scheduled_for=scheduled_for,
        )
        db.add(msg)
        threshold.last_nudge_at = datetime.now()
        await db.commit()
        logger.info(f"Nudge queued for user {user.id} — quiet hours, scheduled for {scheduled_for}")
        return

    # 5. Generate coaching message via GPT-5 Mini
    provider = get_nudge_provider()
    try:
        content = await provider.generate_nudge(COACHING_SYSTEM_PROMPT, user_context)
    except Exception as e:
        logger.error(f"Failed to generate nudge for user {user.id}: {e}")
        return

    # 6. Send push notification
    if user.push_token:
        sent = await send_push_notification(
            push_token=user.push_token,
            title="Situational AI",
            body=content,
            collapse_id=str(threshold.id),  # Collapse duplicates per threshold
        )
    else:
        sent = False
        logger.warning(f"No push token for user {user.id}")

    # 7. Record the message
    msg = CoachingMessage(
        user_id=user.id,
        threshold_id=threshold.id,
        content=content,
        trigger_context=trigger_context,
        model_used=settings.nudge_model,
        message_type="nudge",
        status="sent" if sent else "failed",
    )
    db.add(msg)
    threshold.last_nudge_at = datetime.now()
    await db.commit()


async def _should_send_nudge(threshold: Threshold) -> bool:
    """Idempotency check — enforce minimum interval between nudges per threshold."""
    if threshold.last_nudge_at is None:
        return True

    elapsed = datetime.now() - threshold.last_nudge_at.replace(tzinfo=None)
    min_interval = settings.min_nudge_interval_minutes * 60
    return elapsed.total_seconds() >= min_interval


async def process_queued_nudges(db: AsyncSession) -> int:
    """Process queued nudges that are past their scheduled delivery time.

    Called by a periodic task (cron or background worker).
    Re-checks whether the user is still over threshold before generating content.
    Discards stale nudges where the user is no longer breached.

    Returns the number of nudges processed.
    """
    now = datetime.now()
    result = await db.execute(
        select(CoachingMessage)
        .where(
            CoachingMessage.status == "queued",
            CoachingMessage.scheduled_for <= now,
        )
    )
    queued = result.scalars().all()
    processed = 0

    for msg in queued:
        # Fetch user and threshold
        user_result = await db.execute(select(User).where(User.id == msg.user_id))
        user = user_result.scalar_one_or_none()
        threshold_result = await db.execute(select(Threshold).where(Threshold.id == msg.threshold_id))
        threshold = threshold_result.scalar_one_or_none()

        if not user or not threshold:
            msg.status = "discarded"
            processed += 1
            continue

        # Re-check threshold — user may have gone back under
        breached = await is_threshold_breached(threshold, db)
        if not breached:
            msg.status = "discarded"
            processed += 1
            continue

        # Generate fresh content with current context
        days_count = await get_days_over_threshold(threshold, db)
        trend = await get_trend_summary(threshold, db)
        history = await get_recent_history(threshold, db)

        from backend.app.services.threshold_engine import get_latest_value
        current_value = await get_latest_value(user.id, threshold.metric_type, db)

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

        provider = get_nudge_provider()
        try:
            content = await provider.generate_nudge(COACHING_SYSTEM_PROMPT, user_context)
        except Exception as e:
            logger.error(f"Failed to generate queued nudge: {e}")
            msg.status = "failed"
            processed += 1
            continue

        msg.content = content
        msg.model_used = settings.nudge_model

        if user.push_token:
            sent = await send_push_notification(
                push_token=user.push_token,
                title="Situational AI",
                body=content,
                collapse_id=str(threshold.id),
            )
            msg.status = "sent" if sent else "failed"
        else:
            msg.status = "failed"

        processed += 1

    await db.commit()
    return processed
