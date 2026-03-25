"""Subscription management — App Store Server API.

v0.1: Paid only. Validates transactions via App Store Server API (NOT verifyReceipt).
Future: App Store Server Notifications V2 webhook for real-time entitlement updates.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.routers.auth import get_current_user

router = APIRouter(prefix="/api", tags=["subscriptions"])


class SubscriptionVerifyRequest(BaseModel):
    transaction_id: str
    original_transaction_id: str


class SubscriptionStatus(BaseModel):
    is_active: bool
    tier: str
    expires_at: str | None = None


class PushTokenUpdate(BaseModel):
    push_token: str


@router.post("/subscription/verify", response_model=SubscriptionStatus)
async def verify_subscription(
    request: SubscriptionVerifyRequest,
    authorization: str = Header(""),
    db: AsyncSession = Depends(get_db),
):
    """Validate a StoreKit 2 transaction via App Store Server API.

    v0.1: Simplified — we mark all authenticated users as paid.
    Production: Implement full App Store Server API validation.
    TODO: https://developer.apple.com/documentation/appstoreserverapi
    """
    user = await get_current_user(authorization, db)

    # v0.1: stub — all users are paid
    # Production: validate transaction_id against App Store Server API
    # and update user.subscription_tier accordingly
    user.subscription_tier = "paid"
    await db.commit()

    return SubscriptionStatus(
        is_active=True,
        tier=user.subscription_tier,
    )


@router.post("/push-token")
async def update_push_token(
    request: PushTokenUpdate,
    authorization: str = Header(""),
    db: AsyncSession = Depends(get_db),
):
    """Update the user's APNs push token. Called on app launch and token refresh."""
    user = await get_current_user(authorization, db)
    user.push_token = request.push_token
    await db.commit()
    return {"status": "ok"}


@router.post("/user/settings")
async def update_user_settings(
    timezone: str | None = None,
    quiet_hours: str | None = None,
    authorization: str = Header(""),
    db: AsyncSession = Depends(get_db),
):
    """Update user timezone and quiet hours."""
    user = await get_current_user(authorization, db)
    if timezone is not None:
        user.timezone = timezone
    if quiet_hours is not None:
        user.quiet_hours = quiet_hours
    await db.commit()
    return {"status": "ok"}
