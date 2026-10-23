"""
Remote execution client.

Forwards untrusted Python code to an isolated runner service over HTTPS with
bearer-token authentication. Used by the API server when the local bubblewrap
sandbox cannot run on this host (e.g. Render containers that block unprivileged
user namespaces).  Never falls back to unrestricted local execution.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Optional

RUNNER_URL = os.getenv("FLOWFORGE_RUNNER_URL", "").strip().rstrip("/")
RUNNER_TOKEN = os.getenv("FLOWFORGE_RUNNER_TOKEN", "").strip()


def run_remote(code: str, user_input: str, timeout_sec: float) -> Optional[dict]:
    """Forward `code` to the remote runner and return its JSON result dict.

    Returns None if the runner is not configured or is unreachable.  Never
    raises — callers must treat None as "execution unavailable".
    """
    if not RUNNER_URL or not RUNNER_TOKEN:
        return None
    payload = json.dumps({
        "code": code,
        "user_input": user_input or "",
        "timeout": float(timeout_sec),
    }).encode("utf-8")
    req = urllib.request.Request(
        RUNNER_URL + "/run",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + RUNNER_TOKEN,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec + 10) as resp:
            body = resp.read().decode("utf-8")
    except (urllib.error.HTTPError, urllib.error.URLError, OSError, ValueError) as exc:
        detail = ""
        if isinstance(exc, urllib.error.HTTPError):
            try:
                detail = exc.read().decode("utf-8", "replace")[:200]
            except OSError:
                pass
        return {"status": "error", "mode": "remote", "message":
                f"Runner unreachable: {exc}" + (f" ({detail})" if detail else "")}
    try:
        return json.loads(body)
    except (ValueError, TypeError):
        return {"status": "error", "mode": "remote", "message": "Runner returned invalid response."}
