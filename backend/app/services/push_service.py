"""APNs push notification service.

Uses apns-collapse-id per threshold to collapse duplicate notifications.
This prevents users from receiving multiple nudges from batched HealthKit deliveries.
"""

from __future__ import annotations

import json
import logging

from backend.app.config import settings

logger = logging.getLogger(__name__)


async def send_push_notification(
    push_token: str,
    title: str,
    body: str,
    collapse_id: str | None = None,
) -> bool:
    """Send a push notification via APNs.

    Args:
        push_token: The user's APNs device token.
        title: Notification title.
        body: Notification body (the coaching message).
        collapse_id: apns-collapse-id — use threshold_id to collapse duplicates per threshold.

    Returns:
        True if sent successfully, False otherwise.
    """
    try:
        from aioapns import APNs, NotificationRequest

        apns_client = APNs(
            key=settings.apns_key_path,
            key_id=settings.apns_key_id,
            team_id=settings.apns_team_id,
            topic=settings.apns_topic,
            use_sandbox=settings.apns_use_sandbox,
        )

        payload = {
            "aps": {
                "alert": {
                    "title": title,
                    "body": body,
                },
                "sound": "default",
                "badge": 1,
            }
        }

        request = NotificationRequest(
            device_token=push_token,
            message=payload,
            collapse_key=collapse_id,
        )

        response = await apns_client.send_notification(request)

        if not response.is_successful:
            logger.error(f"APNs delivery failed: {response.description} for token {push_token[:8]}...")
            return False

        return True

    except ImportError:
        logger.warning("aioapns not installed — push notifications disabled")
        return False
    except Exception as e:
        logger.error(f"Push notification error: {e}")
        return False
