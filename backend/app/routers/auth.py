"""Sign in with Apple authentication."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from jose import jwt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models.user import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


class AppleSignInRequest(BaseModel):
    identity_token: str  # JWT from Sign in with Apple
    user_identifier: str  # Apple's stable user ID
    email: str | None = None
    full_name: str | None = None


class AuthResponse(BaseModel):
    access_token: str
    user_id: str


def _create_access_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.utcnow() + timedelta(days=30),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


async def get_current_user(
    authorization: str = "",
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and validate the current user from the Authorization header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authorization")

    token = authorization.removeprefix("Bearer ")
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        user_id = payload.get("sub")
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@router.post("/apple", response_model=AuthResponse)
async def sign_in_with_apple(
    request: AppleSignInRequest,
    db: AsyncSession = Depends(get_db),
):
    """Exchange a Sign in with Apple identity token for an access token.

    On first sign-in, creates the user record. On subsequent sign-ins,
    returns an access token for the existing user.
    """
    # In production: validate the identity_token JWT against Apple's public keys
    # For v0.1, we trust the client-provided user_identifier
    # TODO: Add proper JWT validation against https://appleid.apple.com/auth/keys

    result = await db.execute(
        select(User).where(User.apple_user_id == request.user_identifier)
    )
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            apple_user_id=request.user_identifier,
            email=request.email,
            name=request.full_name,
            subscription_tier="paid",  # v0.1: paid only
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

    token = _create_access_token(str(user.id))
    return AuthResponse(access_token=token, user_id=str(user.id))
