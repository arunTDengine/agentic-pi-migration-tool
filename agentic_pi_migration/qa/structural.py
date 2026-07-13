"""Deterministic QA checks — run before (and feed into) the LLM judge."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any


_OLD_YEAR = re.compile(r"\b(20[01]\d)\b")  # 2000–2019 look archival for demos


def run_structural_checks(
    *,
    report: dict[str, Any] | list[Any],
    display: dict[str, Any] | None,
    tags: list[dict[str, str]] | None,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    rows = report if isinstance(report, list) else [report]
    primary = rows[0] if rows else {}

    failed = list(primary.get("panels_failed") or [])
    live = list(primary.get("panels_live") or [])
    checks.append(
        {
            "id": "panels_live",
            "ok": len(failed) == 0 and (not primary or len(live) > 0 or primary.get("dashboard_type") != "canvas"),
            "critical": True,
            "detail": f"live={live} failed={failed}",
        }
    )
    checks.append(
        {
            "id": "dashboard_url",
            "ok": bool(primary.get("url")),
            "critical": True,
            "detail": primary.get("url") or "missing url",
        }
    )

    time_from = (display or {}).get("time_from") or ""
    time_to = (display or {}).get("time_to") or ""
    checks.append(
        {
            "id": "relative_time_window",
            "ok": str(time_from).startswith("now") and str(time_to) in ("now", "now+0s", ""),
            "critical": False,
            "detail": f"{time_from or '?'} → {time_to or '?'}",
        }
    )

    pens = ((display or {}).get("canvas") or {}).get("pens") or []
    diagonal = 0
    archived_dates = 0
    for pen in pens:
        if pen.get("name") == "line":
            w, h = float(pen.get("width") or 0), float(pen.get("height") or 0)
            if w > 1 and h > 1:
                diagonal += 1
        text = str(pen.get("text") or "")
        if _OLD_YEAR.search(text) and "20" in text:
            # Flag 2000–2019 stamps on the Canvas footer/labels
            year_match = _OLD_YEAR.search(text)
            if year_match and int(year_match.group(1)) < datetime.now().year - 1:
                archived_dates += 1

    checks.append(
        {
            "id": "orthogonal_pipes",
            "ok": diagonal == 0,
            "critical": True,
            "detail": f"diagonal_segments={diagonal}",
        }
    )
    checks.append(
        {
            "id": "no_archived_dates",
            "ok": archived_dates == 0,
            "critical": False,
            "detail": f"archived_label_hits={archived_dates}",
        }
    )

    if tags is not None:
        checks.append(
            {
                "id": "tags_present",
                "ok": len(tags) > 0,
                "critical": True,
                "detail": f"tag_rows={len(tags)}",
            }
        )

    expected_ids = ("main-body", "side-body", "pump-body", "qc", "feed-badge", "lc-valve")
    if pens:
        ids = {str(p.get("id") or "") for p in pens}
        missing = [eid for eid in expected_ids if eid not in ids and not any(eid in i for i in ids)]
        # soft: many layouts use image ids like main-body
        soft_missing = [eid for eid in expected_ids if not any(eid.split("-")[0] in i for i in ids)]
        checks.append(
            {
                "id": "core_elements",
                "ok": len(soft_missing) <= 2,
                "critical": False,
                "detail": f"soft_missing={soft_missing} pen_count={len(pens)}",
            }
        )

    critical_failures = [c for c in checks if c["critical"] and not c["ok"]]
    return {
        "checks": checks,
        "passed": sum(1 for c in checks if c["ok"]),
        "failed": sum(1 for c in checks if not c["ok"]),
        "critical_failures": [c["id"] for c in critical_failures],
        "ok": len(critical_failures) == 0,
    }
