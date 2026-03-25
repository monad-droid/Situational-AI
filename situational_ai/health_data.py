"""Apple Health XML export parser + manual entry fallback.

Apple Health data can be exported from the Health app:
  Health → profile picture → Export All Health Data → export.xml

This module parses that XML and extracts the metrics we care about.
"""

from __future__ import annotations

import sqlite3
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "health.db"

# Apple Health type identifiers → our short metric names
METRIC_MAP = {
    "HKQuantityTypeIdentifierBodyMass": "body_mass",
    "HKQuantityTypeIdentifierHeartRate": "heart_rate",
    "HKQuantityTypeIdentifierStepCount": "steps",
    "HKQuantityTypeIdentifierBloodPressureSystolic": "bp_systolic",
    "HKQuantityTypeIdentifierBloodPressureDiastolic": "bp_diastolic",
    "HKQuantityTypeIdentifierBodyFatPercentage": "body_fat",
    "HKQuantityTypeIdentifierDietaryEnergyConsumed": "calories_consumed",
    "HKQuantityTypeIdentifierActiveEnergyBurned": "calories_burned",
    "HKQuantityTypeIdentifierBloodGlucose": "blood_glucose",
}


@dataclass
class HealthRecord:
    metric: str
    value: float
    unit: str
    recorded_at: datetime
    source: str  # "apple_health" | "manual"


def _init_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS health_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            metric TEXT NOT NULL,
            value REAL NOT NULL,
            unit TEXT NOT NULL,
            recorded_at TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'manual',
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_metric_date
        ON health_records(metric, recorded_at DESC)
    """)
    conn.commit()
    return conn


def get_db() -> sqlite3.Connection:
    return _init_db()


# ---------- Apple Health XML Import ----------


def import_apple_health_xml(xml_path: str | Path) -> int:
    """Parse an Apple Health export.xml and insert records into the local DB.

    Returns the number of records imported.
    """
    xml_path = Path(xml_path)
    if not xml_path.exists():
        raise FileNotFoundError(f"Apple Health export not found: {xml_path}")

    conn = get_db()
    count = 0

    # Use iterparse to handle large files without loading everything into memory
    for event, elem in ET.iterparse(str(xml_path), events=("end",)):
        if elem.tag != "Record":
            continue

        hk_type = elem.attrib.get("type", "")
        metric = METRIC_MAP.get(hk_type)
        if metric is None:
            elem.clear()
            continue

        try:
            value = float(elem.attrib["value"])
        except (KeyError, ValueError):
            elem.clear()
            continue

        unit = elem.attrib.get("unit", "")
        date_str = elem.attrib.get("endDate", elem.attrib.get("startDate", ""))

        try:
            recorded_at = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S %z")
        except ValueError:
            elem.clear()
            continue

        conn.execute(
            "INSERT INTO health_records (metric, value, unit, recorded_at, source) VALUES (?, ?, ?, ?, ?)",
            (metric, value, unit, recorded_at.isoformat(), "apple_health"),
        )
        count += 1

        # Free memory as we go
        elem.clear()

        # Batch commits
        if count % 5000 == 0:
            conn.commit()

    conn.commit()
    conn.close()
    return count


# ---------- Manual Entry ----------


def log_manual_entry(metric: str, value: float, unit: str) -> None:
    conn = get_db()
    conn.execute(
        "INSERT INTO health_records (metric, value, unit, recorded_at, source) VALUES (?, ?, ?, ?, ?)",
        (metric, value, unit, datetime.now().isoformat(), "manual"),
    )
    conn.commit()
    conn.close()


# ---------- Queries ----------


def get_latest(metric: str) -> HealthRecord | None:
    conn = get_db()
    row = conn.execute(
        "SELECT metric, value, unit, recorded_at, source FROM health_records WHERE metric = ? ORDER BY recorded_at DESC LIMIT 1",
        (metric,),
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return HealthRecord(
        metric=row[0],
        value=row[1],
        unit=row[2],
        recorded_at=datetime.fromisoformat(row[3]),
        source=row[4],
    )


def get_history(metric: str, limit: int = 30) -> list[HealthRecord]:
    conn = get_db()
    rows = conn.execute(
        "SELECT metric, value, unit, recorded_at, source FROM health_records WHERE metric = ? ORDER BY recorded_at DESC LIMIT ?",
        (metric, limit),
    ).fetchall()
    conn.close()
    return [
        HealthRecord(metric=r[0], value=r[1], unit=r[2], recorded_at=datetime.fromisoformat(r[3]), source=r[4])
        for r in rows
    ]
