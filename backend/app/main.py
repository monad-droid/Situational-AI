"""Situational AI — Backend API.

FastAPI server for the Situational AI iOS health coaching app.
Handles sample ingestion, threshold evaluation, coaching generation,
push notifications, and subscription management.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.app.database import Base, engine
from backend.app.routers import auth, chat, samples, subscriptions, thresholds


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables on startup (dev only — use Alembic migrations in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="Situational AI",
    description="Threshold-triggered health coaching API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(auth.router)
app.include_router(samples.router)
app.include_router(thresholds.router)
app.include_router(chat.router)
app.include_router(subscriptions.router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "0.1.0"}
