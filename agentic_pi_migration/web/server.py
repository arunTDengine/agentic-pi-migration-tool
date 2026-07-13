"""FastAPI server for the Agentic PI Migration Upgrade web UI."""

from __future__ import annotations

import json
import os
import shutil
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agentic_pi_migration.client import IdmpClient
from agentic_pi_migration.folder_intake import ingest_folder
from agentic_pi_migration.idmp_compat import COMMON_IDMP_PORTS, discover_local_idmp
from agentic_pi_migration.loader import load_dashboards
from agentic_pi_migration.migrator import AgenticPiMigrator, PI_TO_IDMP_PANEL
from agentic_pi_migration.qa import run_quality_check
from agentic_pi_migration.qa.llm import llm_config_from_env

ROOT = Path(__file__).resolve().parents[2]
WEB_DIR = ROOT / "web"
UPLOADS_DIR = ROOT / "uploads"
SCENARIOS_DIR = ROOT / "scenarios"

BUILTIN_EXAMPLES: dict[str, str] = {
    "summit-creek-oil": "Summit Creek oil — 3 dashboards (ops, P-101, SEP-101)",
    "examples/ops-overview": "Single display folder intake example",
    "examples/pump-train-pnid": "Editable P&ID — animated pump train Canvas",
    "examples/houston-refinery-pivision": "PI Vision image demo — Houston refinery column",
}


def _load_dotenv() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    import os

    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip("'\"")
        os.environ.setdefault(key, value)


_load_dotenv()
UPLOADS_DIR = Path(os.environ.get("UPLOADS_DIR", str(ROOT / "uploads"))).resolve()

app = FastAPI(
    title="Agentic PI Migration Upgrade",
    description="Web UI for PI Vision to TDengine IDMP dashboard migration",
    version="1.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

jobs: dict[str, dict[str, Any]] = {}


class ValidateRequest(BaseModel):
    idmp_url: str = "http://localhost:6042"
    user: str = ""
    password: str = ""
    api_key: str = ""
    keyword: str = "SCE"


class ExampleIngestRequest(BaseModel):
    example_id: str
    target_element_id: int | None = Field(default=None, gt=0)


class MigrateRequest(BaseModel):
    job_id: str
    idmp_url: str = "http://localhost:7142"
    user: str = ""
    password: str = ""
    api_key: str = ""
    create_new: bool = False
    workers: int = Field(default=3, ge=1, le=8)
    prompt_context: str = ""
    panel_prompts: dict[str, str] = Field(default_factory=dict)
    run_qa: bool = True
    external_assist: bool | None = None


class QaRequest(BaseModel):
    job_id: str
    structural_only: bool = False
    include_screenshot: bool = True


def _default_config() -> dict[str, Any]:
    qa_cfg = llm_config_from_env()
    return {
        "idmp_url": os.environ.get(
            "IDMP_URL",
            "http://localhost:6042",
        ),
        "user": os.environ.get("IDMP_USER", os.environ.get("IDMP_USERNAME", "")),
        "has_password": bool(os.environ.get("IDMP_PASSWORD")),
        "has_api_key": bool(os.environ.get("IDMP_API_KEY")),
        "has_qa_llm": bool(qa_cfg.get("api_key")),
        "qa_llm_provider": qa_cfg.get("provider"),
        "qa_llm_model": qa_cfg.get("model") if qa_cfg.get("api_key") else None,
        "qa_assist_panels": os.environ.get("QA_LLM_ASSIST_PANELS", "1").strip().lower()
        not in ("0", "false", "no", "off"),
        "default_ports": list(COMMON_IDMP_PORTS),
        "running_in_docker": bool(os.environ.get("RUNNING_IN_DOCKER")),
    }


def _safe_extract_zip(zip_path: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path) as zf:
        for member in zf.namelist():
            target = (dest / member).resolve()
            if not str(target).startswith(str(dest.resolve())):
                raise HTTPException(status_code=400, detail="Invalid zip entry path")
        zf.extractall(dest)


def _normalize_upload_root(folder: Path) -> Path:
    """If zip contained a single top-level folder, use it as the migration root."""
    entries = [p for p in folder.iterdir() if not p.name.startswith(".")]
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return folder


def _scenario_summary(scenario: dict[str, Any]) -> dict[str, Any]:
    displays = scenario.get("displays", [scenario])
    return {
        "name": scenario.get("name", "Migration"),
        "description": scenario.get("description", ""),
        "source_folder": scenario.get("source_folder"),
        "display_count": len(displays),
        "displays": [
            {
                "name": d.get("name"),
                "element_id": d.get("element_id"),
                "dashboard_id": d.get("dashboard_id"),
                "dashboard_type": d.get("dashboard_type", "grid"),
                "theme": d.get("theme"),
                "panel_count": len(d.get("panels", [])),
                "has_screenshot": bool(d.get("reference_screenshot")),
                "has_canvas_plan": bool(d.get("canvas")),
                "canvas_equipment_count": len((d.get("canvas") or {}).get("equipment", [])),
                "canvas_flow_count": len((d.get("canvas") or {}).get("flows", [])),
                "panels": [
                    {
                        "key": p.get("key"),
                        "title": p.get("title"),
                        "type": p.get("type"),
                        "element_id": p.get("element_id"),
                        "pi_tags": p.get("pi_tags", []),
                        "prompt": p.get("prompt", ""),
                    }
                    for p in d.get("panels", [])
                ],
            }
            for d in displays
        ],
    }


def _retarget_scenario(scenario: dict[str, Any], element_id: int) -> None:
    """Point a built-in example at an element selected from the user's IDMP."""
    displays = scenario.get("displays", [scenario])
    for display in displays:
        display["element_id"] = element_id
        display["dashboard_id"] = None
        for panel in display.get("panels", []):
            panel["element_id"] = element_id
        for equipment in (display.get("canvas") or {}).get("equipment", []):
            binding = equipment.get("binding")
            if binding:
                binding["element_id"] = element_id


def _create_job(
    scenario: dict[str, Any],
    *,
    source: str,
    scenario_path: Path,
    folder_path: Path | None = None,
) -> dict[str, Any]:
    job_id = uuid.uuid4().hex[:12]
    resolved_folder = folder_path or (
        Path(scenario["source_folder"]) if scenario.get("source_folder") else None
    )
    job = {
        "id": job_id,
        "source": source,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scenario_path": str(scenario_path),
        "folder_path": str(resolved_folder) if resolved_folder else None,
        "summary": _scenario_summary(scenario),
    }
    jobs[job_id] = job
    return job


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "agentic-pi-migration-ui"}


@app.get("/api/config")
def get_config() -> dict[str, Any]:
    return _default_config()


@app.get("/api/discover")
def discover_idmp() -> dict[str, Any]:
    instances = discover_local_idmp()
    return {"instances": instances, "count": len(instances)}


@app.get("/api/map-types")
def map_types() -> list[dict[str, str]]:
    return [{"pi_vision": pi, "idmp": idmp} for pi, idmp in sorted(PI_TO_IDMP_PANEL.items())]


@app.get("/api/examples")
def list_examples() -> list[dict[str, Any]]:
    items = []
    for example_id, label in BUILTIN_EXAMPLES.items():
        path = SCENARIOS_DIR / f"{example_id}.json" if "/" not in example_id else None
        if example_id.startswith("examples/"):
            folder = SCENARIOS_DIR / example_id
            available = folder.is_dir()
        else:
            available = path is not None and path.exists()
        items.append({"id": example_id, "label": label, "available": available})
    return items


@app.post("/api/validate")
def validate_connection(body: ValidateRequest) -> dict[str, Any]:
    try:
        client = IdmpClient(
            body.idmp_url,
            body.user,
            body.password,
            api_key=body.api_key or None,
        )
        rows = client.search_elements(body.keyword, limit=20)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "ok": True,
        "idmp_url": client.base_url,
        "requested_url": body.idmp_url,
        "profile": client.profile.to_dict(),
        "keyword": body.keyword,
        "element_count": len(rows),
        "elements": [
            {"id": row["id"], "name": row.get("name"), "type": row.get("type")}
            for row in rows[:20]
        ],
    }


@app.post("/api/ingest/upload")
async def ingest_upload(file: UploadFile = File(...)) -> dict[str, Any]:
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Upload a .zip file containing your migration folder")

    job_dir = UPLOADS_DIR / uuid.uuid4().hex[:12]
    job_dir.mkdir(parents=True, exist_ok=True)
    zip_path = job_dir / "upload.zip"

    try:
        content = await file.read()
        max_bytes = int(os.environ.get("MAX_UPLOAD_MB", "100")) * 1024 * 1024
        if len(content) > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"Upload exceeds the {max_bytes // (1024 * 1024)} MB limit.",
            )
        zip_path.write_bytes(content)
        extract_dir = job_dir / "folder"
        _safe_extract_zip(zip_path, extract_dir)
        root = _normalize_upload_root(extract_dir)
        scenario = ingest_folder(root)
        scenario_path = job_dir / "scenario.json"
        scenario_path.write_text(json.dumps(scenario, indent=2), encoding="utf-8")
    except HTTPException:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise
    except Exception as exc:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    job = _create_job(
        scenario,
        source=f"upload:{file.filename}",
        scenario_path=scenario_path,
        folder_path=root,
    )
    return {"job_id": job["id"], "summary": job["summary"]}


@app.post("/api/ingest/example")
def ingest_example(body: ExampleIngestRequest) -> dict[str, Any]:
    example_id = body.example_id
    if example_id not in BUILTIN_EXAMPLES:
        raise HTTPException(status_code=404, detail=f"Unknown example: {example_id}")

    job_dir = UPLOADS_DIR / uuid.uuid4().hex[:12]
    job_dir.mkdir(parents=True, exist_ok=True)
    scenario_path = job_dir / "scenario.json"
    folder_path: Path | None = None

    try:
        if example_id.startswith("examples/"):
            folder = SCENARIOS_DIR / example_id
            if not folder.is_dir():
                raise HTTPException(status_code=404, detail=f"Example folder not found: {example_id}")
            scenario = ingest_folder(folder)
            folder_path = folder
        else:
            src = SCENARIOS_DIR / f"{example_id}.json"
            if not src.exists():
                raise HTTPException(status_code=404, detail=f"Example scenario not found: {example_id}")
            scenario = json.loads(src.read_text(encoding="utf-8"))
        if body.target_element_id is not None:
            _retarget_scenario(scenario, body.target_element_id)
        scenario_path.write_text(json.dumps(scenario, indent=2), encoding="utf-8")
    except HTTPException:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise
    except Exception as exc:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    job = _create_job(
        scenario,
        source=f"example:{example_id}",
        scenario_path=scenario_path,
        folder_path=folder_path,
    )
    return {"job_id": job["id"], "summary": job["summary"]}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, Any]:
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.post("/api/migrate")
def migrate(body: MigrateRequest) -> dict[str, Any]:
    job = jobs.get(body.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found. Re-upload or re-select your scenario.")

    scenario_path = Path(job["scenario_path"])
    if not scenario_path.exists():
        raise HTTPException(status_code=404, detail="Scenario file missing on server")

    try:
        client = IdmpClient(
            body.idmp_url,
            body.user,
            body.password,
            api_key=body.api_key or None,
        )
        migrator = AgenticPiMigrator(
            client,
            workers=body.workers,
            prompt_context=body.prompt_context.strip(),
            external_assist=body.external_assist,
        )
        dashboards = load_dashboards(scenario_path)
        if body.panel_prompts:
            for spec in dashboards:
                for panel in spec.panels:
                    if panel.key in body.panel_prompts:
                        panel.prompt = body.panel_prompts[panel.key]
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    results: list[dict[str, Any]] = []
    errors: list[str] = []

    for spec in dashboards:
        try:
            result = migrator.migrate_dashboard(spec, update_existing=not body.create_new)
            results.append(result)
        except Exception as exc:
            errors.append(f"{spec.name}: {exc}")

    job["migration"] = {
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "prompt_context": body.prompt_context.strip(),
        "panel_prompts": body.panel_prompts,
        "results": results,
        "errors": errors,
    }
    report_path = Path(job["scenario_path"]).with_name("migration-report.json")
    report_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    job["report_path"] = str(report_path)

    return {
        "ok": len(errors) == 0,
        "migrated": len(results),
        "failed": len(errors),
        "results": results,
        "errors": errors,
        "report_path": str(report_path),
        "qa_available": bool(llm_config_from_env().get("api_key")),
    }


@app.post("/api/qa/stream")
def qa_stream(body: QaRequest) -> StreamingResponse:
    """NDJSON stream of QA agent progress + final judgment (for Studio loading UI)."""
    job = jobs.get(body.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    report_path = Path(job.get("report_path") or "")
    if not report_path.exists():
        # fall back to writing from last migration results
        results = (job.get("migration") or {}).get("results")
        if not results:
            raise HTTPException(status_code=400, detail="No migration report yet — publish first.")
        report_path = Path(job["scenario_path"]).with_name("migration-report.json")
        report_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
        job["report_path"] = str(report_path)

    folder = Path(job["folder_path"]) if job.get("folder_path") else None
    use_llm = not body.structural_only and bool(llm_config_from_env().get("api_key"))

    def generate():
        import queue
        import threading

        events: queue.Queue[dict[str, Any] | None] = queue.Queue()

        def on_progress(event: dict[str, Any]) -> None:
            # keep stream light — drop huge nested result until final
            payload = {k: v for k, v in event.items() if k != "result"}
            if "judgment" in payload and isinstance(payload["judgment"], dict):
                j = payload["judgment"]
                payload["judgment"] = {
                    "verdict": j.get("verdict"),
                    "overall_score": j.get("overall_score"),
                    "strengths": j.get("strengths"),
                    "issues": j.get("issues"),
                    "fixes": j.get("fixes"),
                    "dimensions": j.get("dimensions"),
                }
            events.put({"type": "progress", **payload})

        def worker() -> None:
            try:
                events.put(
                    {
                        "type": "progress",
                        "stage": "start",
                        "message": (
                            "Starting external LLM quality-check agent…"
                            if use_llm
                            else "Starting structural quality checks…"
                        ),
                        "use_llm": use_llm,
                    }
                )
                result = run_quality_check(
                    report_path,
                    folder=folder,
                    out_path=report_path.with_name("qa-report.json"),
                    use_llm=use_llm,
                    include_screenshot=body.include_screenshot,
                    on_progress=on_progress,
                )
                job["qa"] = result
                events.put({"type": "final", "result": result})
            except Exception as exc:
                events.put({"type": "error", "message": str(exc)})
            finally:
                events.put(None)

        threading.Thread(target=worker, daemon=True).start()
        while True:
            item = events.get()
            if item is None:
                break
            yield json.dumps(item, default=str) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")


@app.get("/")
def index() -> FileResponse:
    index_path = WEB_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Web UI not found")
    return FileResponse(index_path)


if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=WEB_DIR), name="static")


def main() -> None:
    import uvicorn

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    host = os.environ.get("UI_HOST", "127.0.0.1")
    port = int(os.environ.get("UI_PORT", "8765"))
    uvicorn.run(
        "agentic_pi_migration.web.server:app",
        host=host,
        port=port,
        reload=os.environ.get("UI_RELOAD", "").lower() in ("1", "true", "yes"),
    )


if __name__ == "__main__":
    main()
