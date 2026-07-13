"""Scoring rubric for the post-migrate QA agent."""

from __future__ import annotations

RUBRIC_VERSION = "1.0"

DIMENSIONS = [
    {
        "id": "topology",
        "weight": 20,
        "question": "Does the Canvas preserve the PI Vision process topology (feed → column → outlets)?",
    },
    {
        "id": "precision",
        "weight": 15,
        "question": "Are pipes orthogonal, tags/labels non-overlapping, and equipment spaced on a clean grid?",
    },
    {
        "id": "live_data",
        "weight": 20,
        "question": "Are PV/SP and trends bound to live historian tags with a relative now-* → now window?",
    },
    {
        "id": "modernity",
        "weight": 15,
        "question": "Does the IDMP display look more modern/operator-ready than old-school PI Vision chrome?",
    },
    {
        "id": "completeness",
        "weight": 15,
        "question": "Are all expected elements present (columns, valves, pump, Feed QC, product outlets, trend panels)?",
    },
    {
        "id": "demo_ready",
        "weight": 15,
        "question": "Would this be safe to show in a customer demo (no garbled panels, no frozen 2020 dates, LIVE feel)?",
    },
]


SYSTEM_PROMPT = """You are a senior industrial UX + PI Vision migration QA agent.
You review evidence from an Agentic PI → TDengine IDMP Canvas migration.
Be strict, concrete, and demo-oriented. Never invent dashboard content that is not in the evidence.
Score each rubric dimension 0–100. Prefer lower scores when live panels failed or structural checks failed.
Return ONLY valid JSON matching the schema the user provides.
"""


def user_prompt(evidence_summary: str, structural: dict) -> str:
    dims = "\n".join(
        f"- {d['id']} (weight {d['weight']}): {d['question']}" for d in DIMENSIONS
    )
    return f"""## Rubric dimensions
{dims}

## Structural checks (deterministic; already run)
```json
{structural}
```

## Evidence pack
{evidence_summary}

## Response schema (JSON only)
{{
  "verdict": "pass" | "fail" | "needs_review",
  "overall_score": 0-100,
  "dimensions": [
    {{"id": "<dimension id>", "score": 0-100, "notes": "one short sentence"}}
  ],
  "strengths": ["..."],
  "issues": ["actionable issue", "..."],
  "fixes": ["concrete fix the migration agent should do", "..."]
}}

Weighted overall_score = sum(score * weight) / sum(weights).
verdict = pass if overall_score >= 75 and no critical structural failures; fail if overall_score < 60 or any critical structural failure; else needs_review.
"""
