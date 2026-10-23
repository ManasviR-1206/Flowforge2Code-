"""
FlowForge remote execution runner.

A standalone FastAPI service that executes untrusted Python code inside the
bubblewrap sandbox and returns the result.  Intended to be deployed on a host
that supports unprivileged user namespaces (the API server itself may not, e.g.
Render containers).  Authenticates callers with a bearer token and never runs
code without sandbox isolation.

Run with:
    FLOWFORGE_RUNNER_TOKEN=<secret> uvicorn runner_server:app --host 0.0.0.0 --port 8001
"""
from __future__ import annotations

import os
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

import executor

app = FastAPI(title="FlowForge Remote Runner", version="1.0.0")

RUNNER_TOKEN = os.getenv("FLOWFORGE_RUNNER_TOKEN", "").strip()


class RunRequest(BaseModel):
    code: str
    user_input: str = ""
    timeout: float = 5.0


@app.get("/api/health")
async def health():
    """Liveness/readiness probe.  Reports whether the local sandbox is usable."""
    return {
        "status": "ok",
        "service": "flowforge-runner",
        "execution": executor.execution_status(block=False),
    }


@app.post("/run")
async def run(req: RunRequest, authorization: Optional[str] = Header(None)):
    """Execute `code` in the sandbox.  Requires Bearer token auth."""
    if not RUNNER_TOKEN:
        raise HTTPException(503, "Runner not configured (missing FLOWFORGE_RUNNER_TOKEN).")
    if authorization != "Bearer " + RUNNER_TOKEN:
        raise HTTPException(401, "Unauthorized.")
    if not 0.5 <= float(req.timeout) <= 30.0:
        raise HTTPException(400, "Timeout must be between 0.5 and 30 seconds.")

    # client_is_local=True: the caller (API server) is trusted to have done its
    # own policy checks, but the runner re-applies them as defence in depth.
    result = executor.execute(req.code, req.user_input, req.timeout, client_is_local=True)

    return {
        "status": result.status,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
        "timed_out": result.timed_out,
        "truncated": result.truncated,
        "leaked_processes": result.leaked_processes,
        "message": result.message,
    }
