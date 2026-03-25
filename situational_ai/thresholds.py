"""Threshold engine — decides when the AI coach should activate.

A threshold is crossed when a health metric goes past a user-defined boundary.
The coach stays active until the metric returns to (or past) the goal value.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path

from situational_ai.health_data import get_latest

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "health.db"


class Direction(str, Enum):
    ABOVE = "above"
    BELOW = "below"


class ThresholdStatus(str, Enum):
    INACTIVE = "inactive"  # metric is fine, coach sleeps
    TRIGGERED = "triggered"  # metric crossed threshold, coach is active
    GOAL_MET = "goal_met"  # user hit the goal, coach celebrates and deactivates


@dataclass
class Threshold:
    id: str
    metric: str
    direction: Direction
    value: float
    unit: str
    goal_value: float
    coach_persona: str

    @classmethod
    def from_dict(cls, d: dict) -> Threshold:
        return cls(
            id=d["id"],
            metric=d["metric"],
            direction=Direction(d["direction"]),
            value=d["value"],
            unit=d["unit"],
            goal_value=d["goal_value"],
            coach_persona=d.get("coach_persona", "You are a motivating health coach."),
        )


@dataclass
class ThresholdState:
    threshold_id: str
    status: ThresholdStatus
    triggered_at: datetime | None
    current_value: float | None
    last_coach_message_at: datetime | None


def _init_state_table() -> None:
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS threshold_state (
            threshold_id TEXT PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'inactive',
            triggered_at TEXT,
            current_value REAL,
            last_coach_message_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS coach_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            threshold_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()


_init_state_table()


def _get_state(threshold_id: str) -> ThresholdState:
    conn = sqlite3.connect(str(DB_PATH))
    row = conn.execute(
        "SELECT threshold_id, status, triggered_at, current_value, last_coach_message_at FROM threshold_state WHERE threshold_id = ?",
        (threshold_id,),
    ).fetchone()
    conn.close()
    if row is None:
        return ThresholdState(
            threshold_id=threshold_id,
            status=ThresholdStatus.INACTIVE,
            triggered_at=None,
            current_value=None,
            last_coach_message_at=None,
        )
    return ThresholdState(
        threshold_id=row[0],
        status=ThresholdStatus(row[1]),
        triggered_at=datetime.fromisoformat(row[2]) if row[2] else None,
        current_value=row[3],
        last_coach_message_at=datetime.fromisoformat(row[4]) if row[4] else None,
    )


def _save_state(state: ThresholdState) -> None:
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        """INSERT INTO threshold_state (threshold_id, status, triggered_at, current_value, last_coach_message_at)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(threshold_id) DO UPDATE SET
               status=excluded.status,
               triggered_at=excluded.triggered_at,
               current_value=excluded.current_value,
               last_coach_message_at=excluded.last_coach_message_at""",
        (
            state.threshold_id,
            state.status.value,
            state.triggered_at.isoformat() if state.triggered_at else None,
            state.current_value,
            state.last_coach_message_at.isoformat() if state.last_coach_message_at else None,
        ),
    )
    conn.commit()
    conn.close()


def save_coach_message(threshold_id: str, role: str, content: str) -> None:
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        "INSERT INTO coach_history (threshold_id, role, content) VALUES (?, ?, ?)",
        (threshold_id, role, content),
    )
    conn.commit()
    conn.close()


def get_coach_history(threshold_id: str, limit: int = 20) -> list[dict]:
    conn = sqlite3.connect(str(DB_PATH))
    rows = conn.execute(
        "SELECT role, content FROM coach_history WHERE threshold_id = ? ORDER BY created_at DESC LIMIT ?",
        (threshold_id, limit),
    ).fetchall()
    conn.close()
    # Return in chronological order
    return [{"role": r[0], "content": r[1]} for r in reversed(rows)]


def evaluate_threshold(threshold: Threshold) -> ThresholdState:
    """Check the latest health data against a threshold and update state."""
    state = _get_state(threshold.id)
    record = get_latest(threshold.metric)

    if record is None:
        return state

    state.current_value = record.value

    is_breached = (
        (threshold.direction == Direction.ABOVE and record.value >= threshold.value)
        or (threshold.direction == Direction.BELOW and record.value <= threshold.value)
    )

    goal_reached = (
        (threshold.direction == Direction.ABOVE and record.value <= threshold.goal_value)
        or (threshold.direction == Direction.BELOW and record.value >= threshold.goal_value)
    )

    if state.status == ThresholdStatus.INACTIVE and is_breached:
        state.status = ThresholdStatus.TRIGGERED
        state.triggered_at = datetime.now()
    elif state.status == ThresholdStatus.TRIGGERED and goal_reached:
        state.status = ThresholdStatus.GOAL_MET
    elif state.status == ThresholdStatus.GOAL_MET:
        # Reset after goal celebration
        state.status = ThresholdStatus.INACTIVE
        state.triggered_at = None

    _save_state(state)
    return state


def get_all_triggered(thresholds: list[Threshold]) -> list[tuple[Threshold, ThresholdState]]:
    """Return all thresholds that are currently triggered (coach should be active)."""
    results = []
    for t in thresholds:
        state = evaluate_threshold(t)
        if state.status == ThresholdStatus.TRIGGERED:
            results.append((t, state))
    return results
