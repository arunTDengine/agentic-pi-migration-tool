#!/usr/bin/env python3
"""Stream realistic refinery demo values into the mapped GTU historian tags."""

from __future__ import annotations

import base64
import json
import math
import os
import random
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

TSDB_URL = os.environ.get("TSDB_URL", "http://localhost:6841").rstrip("/")
TSDB_USER = os.environ.get("TSDB_USER", "root")
TSDB_PASSWORD = os.environ.get("TSDB_PASSWORD", "taosdata")
INTERVAL_SECONDS = float(os.environ.get("DEMO_INTERVAL_SECONDS", "2"))

TABLES = {
    "scheduled_feed": "gtu_pi.t_52fc001_sv",
    "actual_feed": "gtu_pi.t_52fc001_pv",
    "lc780_pv": "gtu_pi.t_54fc007_pv",
    "lc780_sv": "gtu_pi.t_54fc007_sv",
    "fc009_pv": "gtu_pi.t_54fc001_pv",
    "fc009_sv": "gtu_pi.t_54fc001_sv",
    "plant_flow": "gtu_pi.t_54fy026a_pv",
    "product_flow": "gtu_pi.t_54fy026b_pv",
    "storage_flow": "gtu_pi.t_54fy026c_pv",
}


def execute(sql: str) -> None:
    token = base64.b64encode(f"{TSDB_USER}:{TSDB_PASSWORD}".encode()).decode()
    request = urllib.request.Request(
        f"{TSDB_URL}/rest/sql",
        data=sql.encode(),
        headers={
            "Authorization": f"Basic {token}",
            "Content-Type": "text/plain",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        result = json.load(response)
    if result.get("code") != 0:
        raise RuntimeError(result.get("desc") or str(result))


def values_at(step: int) -> dict[str, float]:
    wave = math.sin(step / 8)
    slow = math.sin(step / 23)
    jitter = lambda amount: random.uniform(-amount, amount)
    values = {
        "scheduled_feed": 2536 + slow * 8,
        "actual_feed": 2540 + wave * 24 + jitter(3),
        "lc780_pv": 2489 + wave * 22 + jitter(4),
        "lc780_sv": 2600 + slow * 6,
        "fc009_pv": 298 + wave * 8 + jitter(2),
        "fc009_sv": 300 + slow * 2,
        "plant_flow": 945 + wave * 18 + jitter(2),
        "product_flow": 942 + math.sin(step / 10 + 1.2) * 16 + jitter(2),
        "storage_flow": 907 + math.sin(step / 12 + 2.1) * 13 + jitter(2),
    }
    return {key: float(round(value)) for key, value in values.items()}


def seed_history() -> None:
    """Backfill eight hours so trend panels look complete immediately."""
    end = datetime.now(timezone.utc)
    points: dict[str, list[str]] = {key: [] for key in TABLES}
    for index in range(241):
        timestamp = end - timedelta(minutes=(240 - index) * 2)
        values = values_at(index)
        ts = timestamp.isoformat(timespec="milliseconds").replace("+00:00", "Z")
        for key in TABLES:
            points[key].append(f"('{ts}', {values[key]:g})")
    for key, table in TABLES.items():
        execute(f"INSERT INTO {table} VALUES " + " ".join(points[key]))
    print("Seeded eight hours of realistic trend history.", flush=True)


def main() -> None:
    print(f"Streaming Houston refinery demo data to {TSDB_URL}")
    print("Press Ctrl+C to stop.")
    if os.environ.get("DEMO_SKIP_HISTORY", "").lower() not in ("1", "true", "yes"):
        seed_history()
    step = 241
    while True:
        values = values_at(step)
        for key, table in TABLES.items():
            execute(f"INSERT INTO {table} VALUES (NOW, {values[key]:g})")
        if step % 5 == 0:
            print(
                f"feed={values['actual_feed']:.0f}  "
                f"lc780={values['lc780_pv']:.0f}  "
                f"fc009={values['fc009_pv']:.0f}  "
                f"plant={values['plant_flow']:.0f}",
                flush=True,
            )
        step += 1
        time.sleep(INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nDemo data stopped.")
    except (RuntimeError, urllib.error.URLError) as exc:
        raise SystemExit(f"Unable to write demo data: {exc}") from exc
