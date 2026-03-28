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


class UserSettingsRequest(BaseModel):
    timezone: str | None = None
    quiet_hours: str | None = None
    coach_persona: str | None = None


@router.post("/user/settings")
async def update_user_settings(
    request: UserSettingsRequest,
    authorization: str = Header(""),
    db: AsyncSession = Depends(get_db),
):
    """Update user settings."""
    user = await get_current_user(authorization, db)
    if request.timezone is not None:
        user.timezone = request.timezone
    if request.quiet_hours is not None:
        user.quiet_hours = request.quiet_hours
    if request.coach_persona is not None:
        user.coach_persona = request.coach_persona
    await db.commit()
    return {"status": "ok"}


COACH_PERSONAS = {
    "tough_love": "You are a tough-love coach. Direct, no-nonsense, but you genuinely care. You don't sugarcoat anything. You tell it like it is and expect results, not excuses.",
    "drill_sergeant": "You are a drill sergeant coach. You bark orders. You do NOT accept excuses. You are loud, intense, and in-your-face. Every message feels like you're standing over them screaming. You use military metaphors. 'Drop and give me 20' energy. But underneath the intensity, you believe in them — you just show it by pushing harder.",
    "brutal_honesty": "You are brutally, savagely honest. You roast the user. You call them out with zero filter. You use harsh language, profanity, and dark humor. You might call them lazy, soft, or worse. You are the friend who tells you that you look terrible and means it. You are NOT mean-spirited — you're the wake-up call they asked for. They signed up for this. Make them uncomfortable enough to change. Swear freely. No corporate politeness.",
    "supportive": "You are a warm, supportive coach. You focus on positive reinforcement and small wins. You acknowledge struggles empathetically but always redirect toward action. You celebrate progress genuinely. Think encouraging best friend who also happens to be a personal trainer.",
    "stoic": "You are a stoic philosopher coach. You reference Marcus Aurelius, Epictetus, and Seneca. You frame health as discipline, not motivation. You speak in calm, measured tones about duty to oneself. You remind them that suffering is optional but discipline is required. Brief, powerful, philosophical.",
}


@router.get("/coach-personas")
async def list_personas():
    """Return available coach personas."""
    return {
        "personas": [
            {"id": "tough_love", "name": "Tough Love", "description": "Direct and no-nonsense. Tells it like it is.", "preview": "You've been over your threshold for a week. Stop making excuses and start making changes. Today."},
            {"id": "drill_sergeant", "name": "Drill Sergeant", "description": "Military intensity. In your face. No excuses accepted.", "preview": "ON YOUR FEET, SOLDIER. You think that scale is going to move itself? Get your ass to the gym NOW."},
            {"id": "brutal_honesty", "name": "Brutal Honesty", "description": "Zero filter. Roasts you. Uses profanity. The wake-up call you asked for.", "preview": "172 lbs? Again? Bro you said 'starting Monday' three Mondays ago. Put the fork down."},
            {"id": "supportive", "name": "Supportive", "description": "Warm and encouraging. Focuses on small wins.", "preview": "I see you're a bit over your threshold. That's okay — let's focus on one small change today."},
            {"id": "stoic", "name": "Stoic Philosopher", "description": "Calm wisdom. Discipline over motivation.", "preview": "The body achieves what the mind believes. Your threshold is not a suggestion — it is a commitment you made to yourself."},
        ]
    }
