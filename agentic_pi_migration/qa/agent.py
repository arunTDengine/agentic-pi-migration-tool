"""Orchestrate structural checks + optional external LLM judge."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from agentic_pi_migration.qa.evidence import evidence_text, gather_evidence
from agentic_pi_migration.qa.llm import LlmError, chat_judge, llm_config_from_env
from agentic_pi_migration.qa.rubric import DIMENSIONS, SYSTEM_PROMPT, user_prompt
from agentic_pi_migration.qa.structural import run_structural_checks


class QualityCheckAgent:
    """Harnessed QA agent: deterministic checks first, external LLM second."""

    def __init__(self, *, pass_score: int | None = None, use_llm: bool = True) -> None:
        self.pass_score = pass_score if pass_score is not None else int(
            os.environ.get("QA_PASS_SCORE", "75") or "75"
        )
        self.use_llm = use_llm

    def run(
        self,
        report_path: Path,
        *,
        folder: Path | None = None,
        display_path: Path | None = None,
        include_screenshot: bool = True,
        on_progress: Any | None = None,
    ) -> dict[str, Any]:
        def progress(stage: str, message: str, **extra: Any) -> None:
            if on_progress:
                on_progress({"stage": stage, "message": message, **extra})

        progress("gather", "Collecting migration evidence (report, tags, Canvas plan)…")
        pack = gather_evidence(
            report_path=report_path,
            folder=folder,
            display_path=display_path,
            include_screenshot=include_screenshot,
        )
        progress(
            "structural",
            "Running deterministic structural checks…",
            primary=pack.get("primary"),
        )
        structural = run_structural_checks(
            report=pack.get("report") or {},
            display=pack.get("display"),
            tags=pack.get("tags"),
        )
        progress(
            "structural_done",
            f"Structural checks: {structural['passed']} passed, {structural['failed']} failed",
            structural=structural,
        )

        result: dict[str, Any] = {
            "agent": "idmp-panel-quality-check",
            "report_path": str(report_path),
            "folder": str(folder) if folder else None,
            "primary": pack.get("primary"),
            "structural": structural,
            "llm": None,
            "verdict": "fail",
            "overall_score": 0,
            "pass_score": self.pass_score,
        }

        if not self.use_llm:
            result["verdict"] = "pass" if structural["ok"] else "fail"
            result["overall_score"] = 85 if structural["ok"] else 40
            result["issues"] = [
                f"structural:{c['id']} ({c['detail']})"
                for c in structural["checks"]
                if not c["ok"]
            ]
            progress("done", f"Structural-only verdict: {result['verdict']}", result=result)
            return result

        try:
            cfg = llm_config_from_env()
            progress(
                "llm_start",
                f"Calling external LLM judge ({cfg['provider']} / {cfg['model']})…",
                provider=cfg["provider"],
                model=cfg["model"],
            )
            judgment = chat_judge(
                system=SYSTEM_PROMPT,
                user=user_prompt(evidence_text(pack), structural),
                screenshot=pack.get("screenshot") if include_screenshot else None,
                config=cfg,
            )
            progress("llm_done", "LLM feedback received — scoring rubric…", judgment=judgment)
            result["llm"] = {
                "provider": cfg["provider"],
                "model": cfg["model"],
                "judgment": judgment,
            }
            score = int(judgment.get("overall_score") or 0)
            scores = {d["id"]: d.get("score", 0) for d in judgment.get("dimensions") or []}
            if scores and not judgment.get("overall_score"):
                total_w = sum(d["weight"] for d in DIMENSIONS)
                score = int(
                    sum(int(scores.get(d["id"], 0)) * d["weight"] for d in DIMENSIONS) / total_w
                )
            result["overall_score"] = score
            result["issues"] = list(judgment.get("issues") or [])
            result["fixes"] = list(judgment.get("fixes") or [])
            result["strengths"] = list(judgment.get("strengths") or [])
            result["dimensions"] = list(judgment.get("dimensions") or [])

            if structural["critical_failures"] or score < 60:
                result["verdict"] = "fail"
            elif score >= self.pass_score and structural["ok"]:
                result["verdict"] = "pass"
            else:
                result["verdict"] = judgment.get("verdict") or "needs_review"
            progress(
                "done",
                f"QA complete — {result['verdict']} ({score}/{self.pass_score})",
                result=result,
            )
        except LlmError as exc:
            result["llm"] = {"error": str(exc)}
            result["verdict"] = "needs_review" if structural["ok"] else "fail"
            result["overall_score"] = 70 if structural["ok"] else 35
            result["issues"] = [f"llm_unavailable: {exc}"] + [
                f"structural:{c['id']}" for c in structural["checks"] if not c["ok"]
            ]
            progress("llm_error", str(exc), result=result)

        return result


def run_quality_check(
    report_path: Path | str,
    *,
    folder: Path | str | None = None,
    display_path: Path | str | None = None,
    out_path: Path | str | None = None,
    use_llm: bool = True,
    include_screenshot: bool = True,
    on_progress: Any | None = None,
) -> dict[str, Any]:
    agent = QualityCheckAgent(use_llm=use_llm)
    result = agent.run(
        Path(report_path),
        folder=Path(folder) if folder else None,
        display_path=Path(display_path) if display_path else None,
        include_screenshot=include_screenshot,
        on_progress=on_progress,
    )
    if out_path:
        path = Path(out_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2), encoding="utf-8")
        result["out_path"] = str(path)
    return result
