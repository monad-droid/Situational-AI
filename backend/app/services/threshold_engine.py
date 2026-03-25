"""Threshold engine — deterministic evaluation. NO LLM involved.

This is the source of truth for whether a threshold is breached.
Pure boolean logic: value > target (or value < target for "below" direction).
"""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.metric_log import MetricLog
from backend.app.models.threshold import Threshold


async def is_threshold_breached(threshold: Threshold, db: AsyncSession) -> bool:
    """Check if the latest metric value breaches the threshold. Pure comparison."""
    latest = await get_latest_value(threshold.user_id, threshold.metric_type, db)
    if latest is None:
        return False

    if threshold.direction == "above":
        return latest >= threshold.target_value
    return latest <= threshold.target_value


async def get_latest_value(user_id, metric_type: str, db: AsyncSession) -> float | None:
    """Get the most recent value for a metric."""
    result = await db.execute(
        select(MetricLog.value)
        .where(MetricLog.user_id == user_id, MetricLog.metric_type == metric_type)
        .order_by(MetricLog.recorded_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    return row


async def get_days_over_threshold(threshold: Threshold, db: AsyncSession) -> int:
    """Count consecutive days the user has been over/under threshold.

    Walks backward from today, checking one value per day.
    Returns 0 if the latest value is within threshold.
    """
    latest = await get_latest_value(threshold.user_id, threshold.metric_type, db)
    if latest is None:
        return 0

    breached_now = (
        latest >= threshold.target_value if threshold.direction == "above"
        else latest <= threshold.target_value
    )
    if not breached_now:
        return 0

    # Get daily values going back 90 days max
    ninety_days_ago = datetime.now() - timedelta(days=90)
    result = await db.execute(
        select(
            func.date(MetricLog.recorded_at).label("day"),
            func.avg(MetricLog.value).label("avg_value"),
        )
        .where(
            MetricLog.user_id == threshold.user_id,
            MetricLog.metric_type == threshold.metric_type,
            MetricLog.recorded_at >= ninety_days_ago,
        )
        .group_by(func.date(MetricLog.recorded_at))
        .order_by(func.date(MetricLog.recorded_at).desc())
    )
    rows = result.all()

    days = 0
    for row in rows:
        avg_val = row.avg_value
        if threshold.direction == "above" and avg_val >= threshold.target_value:
            days += 1
        elif threshold.direction == "below" and avg_val <= threshold.target_value:
            days += 1
        else:
            break

    return max(days, 1)  # At least 1 if currently breached


async def get_trend_summary(threshold: Threshold, db: AsyncSession) -> str:
    """Generate a human-readable trend summary from recent data."""
    result = await db.execute(
        select(MetricLog.value, MetricLog.recorded_at)
        .where(
            MetricLog.user_id == threshold.user_id,
            MetricLog.metric_type == threshold.metric_type,
        )
        .order_by(MetricLog.recorded_at.desc())
        .limit(7)
    )
    rows = result.all()

    if len(rows) < 2:
        return "Not enough data for trend"

    values = [r.value for r in rows]
    latest = values[0]
    oldest = values[-1]
    diff = latest - oldest

    if abs(diff) < 0.5:
        return "Flat (no significant change)"
    elif diff > 0:
        return f"Trending up (+{diff:.1f} over last {len(values)} readings)"
    else:
        return f"Trending down ({diff:.1f} over last {len(values)} readings)"


async def get_recent_history(threshold: Threshold, db: AsyncSession) -> str:
    """Get last 5 data points as a formatted string."""
    result = await db.execute(
        select(MetricLog.value, MetricLog.unit, MetricLog.recorded_at)
        .where(
            MetricLog.user_id == threshold.user_id,
            MetricLog.metric_type == threshold.metric_type,
        )
        .order_by(MetricLog.recorded_at.desc())
        .limit(5)
    )
    rows = result.all()

    if not rows:
        return "No data yet"

    entries = [f"{r.recorded_at.strftime('%m/%d')}: {r.value} {r.unit}" for r in rows]
    return ", ".join(entries)
