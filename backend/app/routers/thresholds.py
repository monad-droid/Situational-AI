"""Threshold CRUD — create, read, update thresholds.

v0.1: One threshold per user, body weight only.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models.threshold import Threshold
from backend.app.routers.auth import get_current_user

router = APIRouter(prefix="/api", tags=["thresholds"])


class ThresholdCreate(BaseModel):
    metric_type: str = "bodyMass"
    target_value: float
    direction: str = "above"  # "above" | "below"
    unit: str = "lb"


class ThresholdResponse(BaseModel):
    id: str
    metric_type: str
    target_value: float
    direction: str
    unit: str
    is_active: bool
    created_at: datetime


@router.get("/thresholds", response_model=list[ThresholdResponse])
async def list_thresholds(
    authorization: str = Header(""),
    db: AsyncSession = Depends(get_db),
):
    user = await get_current_user(authorization, db)
    result = await db.execute(
        select(Threshold).where(Threshold.user_id == user.id).order_by(Threshold.created_at.desc())
    )
    thresholds = result.scalars().all()
    return [
        ThresholdResponse(
            id=str(t.id),
            metric_type=t.metric_type,
            target_value=t.target_value,
            direction=t.direction,
            unit=t.unit,
            is_active=t.is_active,
            created_at=t.created_at,
        )
        for t in thresholds
    ]


@router.post("/thresholds", response_model=ThresholdResponse)
async def create_threshold(
    request: ThresholdCreate,
    authorization: str = Header(""),
    db: AsyncSession = Depends(get_db),
):
    """Create a new threshold. v0.1: limited to one threshold per user."""
    user = await get_current_user(authorization, db)

    # v0.1: enforce one threshold per user
    result = await db.execute(
        select(Threshold).where(Threshold.user_id == user.id, Threshold.is_active == True)
    )
    existing = result.scalars().all()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="v0.1 supports one threshold per user. Deactivate the existing one first.",
        )

    threshold = Threshold(
        user_id=user.id,
        metric_type=request.metric_type,
        target_value=request.target_value,
        direction=request.direction,
        unit=request.unit,
    )
    db.add(threshold)
    await db.commit()
    await db.refresh(threshold)

    return ThresholdResponse(
        id=str(threshold.id),
        metric_type=threshold.metric_type,
        target_value=threshold.target_value,
        direction=threshold.direction,
        unit=threshold.unit,
        is_active=threshold.is_active,
        created_at=threshold.created_at,
    )
