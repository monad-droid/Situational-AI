"""Quiet hours enforcement.

CRITICAL: Never send push notifications during quiet hours. A 2 AM notification
will cause users to disable notification permissions entirely, permanently killing
the delivery channel. This is a retention-critical rule.

During quiet hours, nudges are queued with a scheduled_for time (when quiet hours end).
At send time, the delivery worker re-checks whether the user is still above threshold.
If not, the queued message is discarded — we never generate stale coaching content.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta

import zoneinfo


def parse_quiet_hours(quiet_hours_str: str | None) -> tuple[time, time] | None:
    """Parse "22:00-07:00" into (start_time, end_time). Returns None if not set."""
    if not quiet_hours_str:
        return None

    try:
        start_str, end_str = quiet_hours_str.split("-")
        start = time.fromisoformat(start_str.strip())
        end = time.fromisoformat(end_str.strip())
        return (start, end)
    except (ValueError, AttributeError):
        return None


def is_in_quiet_hours(user_timezone: str, quiet_hours_str: str | None) -> bool:
    """Check if the current time in the user's timezone falls within quiet hours."""
    parsed = parse_quiet_hours(quiet_hours_str)
    if parsed is None:
        return False

    start, end = parsed
    try:
        tz = zoneinfo.ZoneInfo(user_timezone)
    except (KeyError, zoneinfo.ZoneInfoNotFoundError):
        tz = zoneinfo.ZoneInfo("America/New_York")

    now = datetime.now(tz).time()

    # Handle overnight ranges like 22:00-07:00
    if start <= end:
        return start <= now <= end
    else:
        return now >= start or now <= end


def get_quiet_hours_end(user_timezone: str, quiet_hours_str: str | None) -> datetime | None:
    """Get the datetime when quiet hours end (for scheduling delayed delivery)."""
    parsed = parse_quiet_hours(quiet_hours_str)
    if parsed is None:
        return None

    _, end = parsed
    try:
        tz = zoneinfo.ZoneInfo(user_timezone)
    except (KeyError, zoneinfo.ZoneInfoNotFoundError):
        tz = zoneinfo.ZoneInfo("America/New_York")

    now = datetime.now(tz)
    end_today = now.replace(hour=end.hour, minute=end.minute, second=0, microsecond=0)

    # If quiet hours end is tomorrow (e.g., quiet 22:00-07:00 and it's 23:00)
    if end_today <= now:
        end_today += timedelta(days=1)

    return end_today
