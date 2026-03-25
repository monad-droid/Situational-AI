"""Sample ingestion — the app sends raw HealthKit samples here.

The backend stores, deduplicates, evaluates thresholds, and triggers nudges.
This is the main data pipeline entry point.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
from backend.app.models.metric_log import MetricLog
from backend.app.models.threshold import Threshold
from backend.app.models.user import User
from backend.app.routers.auth import get_current_user
from backend.app.services.nudge_service import process_threshold_check

router = APIRouter(prefix="/api", tags=["samples"])


class SampleInput(BaseModel):
    metric_type: str  # "bodyMass", "stepCount", etc.
    value: float
    unit: str  # "lb", "kg", "steps", "bpm"
    recorded_at: datetime
    source: str = "healthkit"


class SamplesRequest(BaseModel):
    samples: list[SampleInput]


class SamplesResponse(BaseModel):
    ingested: int
    duplicates_skipped: int


@router.post("/samples", response_model=SamplesResponse)
async def ingest_samples(
    request: SamplesRequest,
    authorization: str = Header(""),
    db: AsyncSession = Depends(get_db),
):
    """Receive new HealthKit samples from the iOS app.

    Flow:
    1. Deduplicate against existing records (HealthKit can batch/repeat samples)
    2. Store new samples
    3. Evaluate thresholds for affected metric types
    4. Trigger nudges if thresholds are breached (respects idempotency + quiet hours)
    """
    user = await get_current_user(authorization, db)
    ingested = 0
    skipped = 0

    affected_metrics = set()

    for sample in request.samples:
        # Upsert with conflict handling for deduplication
        stmt = pg_insert(MetricLog).values(
            user_id=user.id,
            metric_type=sample.metric_type,
            value=sample.value,
            unit=sample.unit,
            recorded_at=sample.recorded_at,
            source=sample.source,
        ).on_conflict_do_nothing(
            constraint="uq_metric_sample"
        )
        result = await db.execute(stmt)

        if result.rowcount > 0:
            ingested += 1
            affected_metrics.add(sample.metric_type)
        else:
            skipped += 1

    await db.commit()

    # Evaluate thresholds for affected metrics
    result = await db.execute(
        select(Threshold).where(
            Threshold.user_id == user.id,
            Threshold.is_active == True,
            Threshold.metric_type.in_(affected_metrics),
        )
    )
    thresholds = result.scalars().all()

    for threshold in thresholds:
        await process_threshold_check(user, threshold, db)

    return SamplesResponse(ingested=ingested, duplicates_skipped=skipped)
