"""FastAPI Webhook and Dashboard Application for DevRel Guard."""

from __future__ import annotations
import os
import time
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from devrel_guard.agent.graph import guard_agent
from devrel_guard.cli import BENCHMARK_SCENARIOS
from devrel_guard.github.webhook_handler import WebhookHandler, verify_webhook_signature
from devrel_guard.rules.catalog import catalog

app = FastAPI(
    title="DevRel Guard API",
    description="Autonomous PR & Dependency Breaking-Change Agent API & Dashboard",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class ScanRequest(BaseModel):
    diff: str
    files: Optional[Dict[str, str]] = None
    repo_root: Optional[str] = None


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return HTMLResponse("<h1>DevRel Guard API is running.</h1><p>Visit /docs for API documentation.</p>")


@app.get("/api/scenarios")
async def get_scenarios():
    """Retrieve pre-configured benchmark scenarios for demonstration."""
    result = {}
    for key, data in BENCHMARK_SCENARIOS.items():
        result[key] = {
            "key": key,
            "title": data["title"],
            "diff": data["diff"],
            "files": data["files"],
        }
    return result


@app.get("/api/rules")
async def get_rules():
    """Retrieve all active ecosystem breaking change rules."""
    rules = catalog.get_all_rules()
    return [r.model_dump() for r in rules]


@app.post("/api/scan")
async def scan_pr(req: ScanRequest):
    """Run full DevRel Guard LangGraph agent analysis on a PR diff and source code."""
    start_time = time.time()

    initial_state = {
        "raw_diff": req.diff,
        "source_files": req.files or {},
        "repo_root": req.repo_root,
        "step_history": [],
    }

    try:
        final_state = guard_agent.invoke(initial_state)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Agent analysis failed: {str(e)}")

    duration = time.time() - start_time

    return {
        "passed": final_state.get("passed", True),
        "duration_seconds": round(duration, 3),
        "nodes_scanned": final_state.get("nodes_scanned", 0),
        "dependency_changes": [d.model_dump() for d in final_state.get("dependency_changes", [])],
        "violations": [v.model_dump() for v in final_state.get("violations", [])],
        "fixes": [f.model_dump() for f in final_state.get("verified_fixes") or final_state.get("fixes", [])],
        "review_comments": [c.model_dump() for c in final_state.get("review_comments", [])],
        "refactored_files": final_state.get("refactored_files", {}),
        "summary_markdown": final_state.get("summary_markdown", ""),
        "step_history": final_state.get("step_history", []),
    }


@app.post("/api/webhook")
async def github_webhook(
    request: Request,
    x_github_event: Optional[str] = Header(None),
    x_hub_signature_256: Optional[str] = Header(None),
):
    """GitHub Webhook receiver for pull_request events."""
    body_bytes = await request.body()
    secret = os.getenv("GITHUB_WEBHOOK_SECRET")

    if secret and not verify_webhook_signature(body_bytes, x_hub_signature_256, secret):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    payload = await request.json()
    if x_github_event != "pull_request":
        return {"status": "ignored", "event": x_github_event}

    handler = WebhookHandler()
    result = handler.process_pr_event(payload)
    return result
