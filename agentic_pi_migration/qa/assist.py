"""External LLM co-pilot for IDMP's built-in panel AI.

External model writes a stronger IDMP-oriented prompt (and optional design hints);
IDMP's internal ``/api/v1/ai/panels/create`` still creates the panel.
"""

from __future__ import annotations

import json
import os
from typing import Any

from agentic_pi_migration.qa.llm import LlmError, chat_judge, llm_config_from_env


ASSIST_SYSTEM = """You are a co-pilot for TDengine IDMP's built-in panel AI.
IDMP will receive YOUR prompt verbatim via POST /api/v1/ai/panels/create.
Write prompts that are concrete, industrial, and attribute-accurate.
Never invent tag/attribute names that are not in the evidence.
Prefer live relative time (now-8h → now or now-15m → now), smooth lines, bottom legend, 2 decimals.
Return ONLY valid JSON.
"""


def assist_enabled(explicit: bool | None = None) -> bool:
    if explicit is not None:
        return explicit
    flag = os.environ.get("QA_LLM_ASSIST_PANELS", "1").strip().lower()
    if flag in ("0", "false", "no", "off"):
        return False
    return bool(llm_config_from_env().get("api_key"))


def enrich_idmp_panel_prompt(
    *,
    title: str,
    panel_type: str,
    idmp_type: str,
    prompt: str,
    pi_tags: list[str],
    prompt_context: str = "",
    time_from: str = "now-8h",
    time_to: str = "now",
) -> dict[str, Any]:
    """Ask external LLM to craft a better prompt for IDMP's panel AI."""
    tags = ", ".join(pi_tags) if pi_tags else "(none listed — stay generic but professional)"
    user = f"""Design an IDMP panel-AI prompt for this migrated PI Vision panel.

Title: {title}
Requested PI/chart type: {panel_type}
Target IDMP panelType: {idmp_type}
Existing prompt notes: {prompt}
Historian / attribute tags: {tags}
Global design direction: {prompt_context or "(none)"}
Time window: {time_from} → {time_to}

Return JSON:
{{
  "idmp_prompt": "full prompt string for IDMP AI (1-3 sentences, imperative, mention ONLY the tags above)",
  "preferred_type": "{idmp_type}",
  "series_aliases": ["friendly legend labels aligned 1:1 with tags if tags exist"],
  "notes": "one short sentence on the design intent"
}}
"""
    judgment = chat_judge(system=ASSIST_SYSTEM, user=user, screenshot=None)
    if not isinstance(judgment, dict) or not judgment.get("idmp_prompt"):
        raise LlmError("External assist returned no idmp_prompt")
    judgment["idmp_prompt"] = str(judgment["idmp_prompt"]).strip()
    judgment["preferred_type"] = str(judgment.get("preferred_type") or idmp_type).strip() or idmp_type
    return judgment


def enrich_or_passthrough(
    *,
    base_prompt: str,
    title: str,
    panel_type: str,
    idmp_type: str,
    prompt: str,
    pi_tags: list[str],
    prompt_context: str = "",
    time_from: str = "now-8h",
    time_to: str = "now",
    enabled: bool | None = None,
) -> tuple[str, dict[str, Any] | None]:
    """Return (prompt_for_idmp, assist_meta). Falls back to base_prompt on error/disabled."""
    if not assist_enabled(enabled):
        return base_prompt, None
    try:
        meta = enrich_idmp_panel_prompt(
            title=title,
            panel_type=panel_type,
            idmp_type=idmp_type,
            prompt=prompt,
            pi_tags=pi_tags,
            prompt_context=prompt_context,
            time_from=time_from,
            time_to=time_to,
        )
        return meta["idmp_prompt"], meta
    except (LlmError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        return base_prompt, {"error": str(exc), "fallback": "base_prompt"}
