"""Gather a compact evidence pack for the QA agent (no LLM calls here)."""

from __future__ import annotations

import base64
import csv
import json
import mimetypes
from pathlib import Path
from typing import Any


IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def _load_json(path: Path | None) -> Any:
    if not path or not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _load_tags(folder: Path | None) -> list[dict[str, str]]:
    if not folder:
        return []
    csv_path = folder / "tags.csv"
    if not csv_path.exists():
        return []
    with csv_path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _find_screenshot(folder: Path | None) -> Path | None:
    if not folder:
        return None
    for name in ("screenshot.jpg", "screenshot.jpeg", "screenshot.png", "screenshot.webp"):
        candidate = folder / name
        if candidate.exists():
            return candidate
    for path in sorted(folder.iterdir()):
        if path.suffix.lower() in IMAGE_EXTS and "screenshot" in path.name.lower():
            return path
    return None


def _image_b64(path: Path | None, *, max_bytes: int = 2_500_000) -> dict[str, str] | None:
    if not path or not path.exists():
        return None
    data = path.read_bytes()
    if len(data) > max_bytes:
        return {"path": str(path), "skipped": f"too_large:{len(data)}"}
    mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    return {
        "path": str(path),
        "mime": mime,
        "base64": base64.b64encode(data).decode("ascii"),
    }


def _summarize_display(display: dict[str, Any] | None) -> dict[str, Any]:
    if not display:
        return {}
    canvas = display.get("canvas") or {}
    pens = canvas.get("pens") or []
    ids = [str(p.get("id") or "") for p in pens]
    return {
        "name": display.get("name"),
        "time_from": display.get("time_from"),
        "time_to": display.get("time_to"),
        "refresh_seconds": display.get("refresh_seconds"),
        "pen_count": len(pens),
        "panel_placements": canvas.get("panel_placements") or [],
        "sample_pen_ids": ids[:40],
        "has_feed_qc": any(i.startswith("qc") for i in ids),
        "has_live_chip": any("live" in i for i in ids),
        "header_html_present": bool(display.get("header_html")),
    }


def gather_evidence(
    *,
    report_path: Path,
    folder: Path | None = None,
    display_path: Path | None = None,
    include_screenshot: bool = True,
) -> dict[str, Any]:
    report = _load_json(report_path)
    if display_path is None and folder is not None:
        candidate = folder / "display.json"
        display_path = candidate if candidate.exists() else None
    display = _load_json(display_path)
    tags = _load_tags(folder)
    shot = _find_screenshot(folder) if include_screenshot else None

    rows = report if isinstance(report, list) else [report]
    primary = rows[0] if rows else {}

    return {
        "report_path": str(report_path),
        "folder": str(folder) if folder else None,
        "report": report,
        "primary": {
            "name": primary.get("name"),
            "url": primary.get("url"),
            "edit_url": primary.get("edit_url"),
            "dashboard_id": primary.get("dashboard_id"),
            "panels_live": primary.get("panels_live"),
            "panels_failed": primary.get("panels_failed"),
            "pens": primary.get("pens"),
            "panel_count": primary.get("panel_count"),
        },
        "display_summary": _summarize_display(display),
        "display": display,
        "tags": tags,
        "tag_names": [t.get("tag") or t.get("name") or t.get("attribute") or "" for t in tags][:80],
        "screenshot": _image_b64(shot) if include_screenshot else None,
    }


def evidence_text(pack: dict[str, Any]) -> str:
    """Human/LLM-readable summary (no base64 dump)."""
    shot = pack.get("screenshot") or {}
    shot_note = shot.get("path") or "none"
    if shot.get("skipped"):
        shot_note = f"{shot_note} ({shot['skipped']})"
    elif shot.get("base64"):
        shot_note = f"{shot_note} (vision attached)"
    body = {
        "primary": pack.get("primary"),
        "display_summary": pack.get("display_summary"),
        "tag_count": len(pack.get("tags") or []),
        "tag_names_sample": (pack.get("tag_names") or [])[:30],
        "screenshot": shot_note,
    }
    return json.dumps(body, indent=2)
