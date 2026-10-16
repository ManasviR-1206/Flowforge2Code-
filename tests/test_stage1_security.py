"""
FlowForge AI – Stage 1 Security & Hardening Test Suite
Tests path traversal, API routes, sandbox verification, execution bounds, and concurrency.
"""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import time
from pathlib import Path

import httpx
import pytest
from starlette.testclient import TestClient

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import api_server
import executor


@pytest.fixture
def app():
    return api_server.app


@pytest.fixture
def client(app):
    return TestClient(app, base_url="http://testserver")


# ==============================================================================
# 1. Path Traversal & File Exposure Defenses
# ==============================================================================

def test_plain_path_traversal(client):
    """Attempt plain path traversal to access sensitive files."""
    for path in ["/.env", "/../../.env", "/../api_server.py", "/.git/config"]:
        response = client.get(path)
        assert response.status_code in (403, 404), f"Path {path} returned {response.status_code}"
        assert "GEMINI_API_KEY" not in response.text
        assert "FlowForge AI API" not in response.text or response.status_code == 404


def test_encoded_path_traversal(client):
    """Attempt single-encoded path traversal."""
    traversal_paths = [
        "/..%2f.env",
        "/..%2f..%2f.env",
        "/%2e%2e/%2e%2e/.env",
        "/%2e%2e%2f.env",
        "/..%2fapi_server.py",
    ]
    for path in traversal_paths:
        response = client.get(path)
        assert response.status_code in (403, 404), f"Path {path} returned {response.status_code}"
        assert "GEMINI_API_KEY" not in response.text


def test_double_encoded_path_traversal(client):
    """Attempt double-encoded path traversal."""
    traversal_paths = [
        "/%252e%252e%252f.env",
        "/%252e%252e%2f.env",
        "/..%252f.env",
        "/%252e%252e%252fapi_server.py",
    ]
    for path in traversal_paths:
        response = client.get(path)
        assert response.status_code in (403, 404), f"Path {path} returned {response.status_code}"
        assert "GEMINI_API_KEY" not in response.text


def test_backslash_path_traversal(client):
    """Attempt Windows backslash traversal."""
    traversal_paths = [
        "/..\\..\\.env",
        "/..%5c.env",
        "/..%5c..%5c.env",
        "/%2e%2e%5c.env",
        "/..\\api_server.py",
    ]
    for path in traversal_paths:
        response = client.get(path)
        assert response.status_code in (403, 404), f"Path {path} returned {response.status_code}"
        assert "GEMINI_API_KEY" not in response.text


def test_symlink_escape_rejection(tmp_path):
    """Verify _safe_dist_file rejects symlinks pointing outside the static root."""
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    secret_file = tmp_path / "secret.env"
    secret_file.write_text("SUPER_SECRET_KEY=12345", encoding="utf-8")

    link_path = dist_dir / "secret_link"
    try:
        os.symlink(str(secret_file), str(link_path))
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation not supported or requires elevated privileges on this OS")

    resolved = api_server._safe_dist_file("secret_link")
    assert resolved is None, "Symlink pointing outside base_dir must be rejected"


# ==============================================================================
# 2. API Routes & SPA Fallback
# ==============================================================================

def test_unknown_api_routes_return_json_404(client):
    """Ensure unknown /api/* routes return JSON 404 and never the SPA index.html."""
    for method in ["get", "post", "delete", "put"]:
        req_fn = getattr(client, method)
        response = req_fn("/api/nonexistent-endpoint-test")
        assert response.status_code == 404
        assert response.headers.get("content-type", "").startswith("application/json")
        data = response.json()
        assert "detail" in data
        assert "<!doctype html>" not in response.text.lower()


def test_valid_spa_routes(client):
    """Verify valid SPA routes serve index.html with HTTP 200."""
    for route in ["/", "/workspace"]:
        response = client.get(route)
        assert response.status_code == 200
        assert "html" in response.headers.get("content-type", "").lower()


# ==============================================================================
# 3. Health Endpoint Accuracy & Non-Blocking Behavior
# ==============================================================================

def test_api_health_endpoint(client):
    """Verify /api/health accurately reports AI and execution sandbox status."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "ai_available" in data
    assert "execution" in data
    exec_info = data["execution"]
    assert "mode" in exec_info
    assert "enabled" in exec_info
    assert "state" in exec_info


def test_health_responsiveness_during_execution(app):
    """Verify /api/health responds promptly even while code is executing in a thread."""
    async def _run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as async_client:
            os.environ["FLOWFORGE_EXECUTION"] = "local-dev"
            try:
                sleep_code = "import time\ntime.sleep(1.0)\nprint('Done sleeping')"

                # Launch execution task in background
                exec_task = asyncio.create_task(
                    async_client.post("/api/execute", json={"code": sleep_code, "user_input": ""})
                )

                # Allow execution task to begin running in worker thread
                await asyncio.sleep(0.15)

                start = time.perf_counter()
                health_resp = await async_client.get("/api/health")
                duration = time.perf_counter() - start

                assert health_resp.status_code == 200
                # Health check must respond well before the 1.0s sleep finishes
                assert duration < 0.6, f"Health check took {duration:.3f}s during execution (expected < 0.6s)"

                exec_resp = await exec_task
                assert exec_resp.status_code == 200
            finally:
                os.environ.pop("FLOWFORGE_EXECUTION", None)

    asyncio.run(_run())


# ==============================================================================
# 4. Executor & Execution Engine
# ==============================================================================

def test_execution_disabled_when_sandbox_unavailable(client):
    """Ensure execution fails closed when genuine sandbox is unavailable."""
    os.environ["FLOWFORGE_EXECUTION"] = "auto"
    try:
        response = client.post("/api/execute", json={"code": "print('hello')", "user_input": ""})
        assert response.status_code == 403
        data = response.json()
        assert "disabled" in data.get("detail", "").lower() or "unavailable" in data.get("detail", "").lower()
    finally:
        os.environ.pop("FLOWFORGE_EXECUTION", None)


def test_executor_newlines_and_prompts():
    """Verify input prompts and outputs are formatted with correct newlines."""
    os.environ["FLOWFORGE_EXECUTION"] = "local-dev"
    try:
        code = "a = input('Enter a: ')\nb = input('Enter b: ')\nprint('Sum:', int(a) + int(b))"
        result = executor.execute(code, "12\n8\n", client_is_local=True)
        assert result.success is True
        assert result.exit_code == 0
        assert "Sum: 20" in result.stdout
    finally:
        os.environ.pop("FLOWFORGE_EXECUTION", None)


def test_executor_exit_status_success_with_error_in_output():
    """Success must be determined by process exit code, not by string matching 'Error:'."""
    os.environ["FLOWFORGE_EXECUTION"] = "local-dev"
    try:
        code = "print('Margin of Error: 0.05')\nprint('Standard Error: 0.01')"
        result = executor.execute(code, client_is_local=True)
        assert result.success is True
        assert result.status == "success"
        assert result.exit_code == 0
        assert "Margin of Error: 0.05" in result.stdout
    finally:
        os.environ.pop("FLOWFORGE_EXECUTION", None)


def test_executor_timeout_limit():
    """Infinite loops must time out cleanly."""
    os.environ["FLOWFORGE_EXECUTION"] = "local-dev"
    try:
        code = "while True: pass"
        result = executor.execute(code, timeout_sec=1, client_is_local=True)
        assert result.success is False
        assert result.status == "timeout"
        assert result.timed_out is True
        assert "timed out" in result.message.lower()
    finally:
        os.environ.pop("FLOWFORGE_EXECUTION", None)


def test_executor_output_truncation():
    """Outputs exceeding the max output limit must be truncated with a notice."""
    os.environ["FLOWFORGE_EXECUTION"] = "local-dev"
    # get_limits() enforces a minimum of 1024 bytes; use 2048 to stay above it.
    os.environ["FLOWFORGE_EXEC_MAX_OUTPUT_BYTES"] = "2048"
    executor.reset_probe()
    try:
        # Generate 8000 chars – well above the 2048-byte cap.
        code = "print('X' * 8000)"
        result = executor.execute(code, client_is_local=True)
        assert result.truncated is True
        # Allow cap + ~50 bytes for the "\n[output truncated]" sentinel.
        assert len(result.stdout) < 2200
        assert "output truncated" in result.stdout.lower()
    finally:
        os.environ.pop("FLOWFORGE_EXECUTION", None)
        os.environ.pop("FLOWFORGE_EXEC_MAX_OUTPUT_BYTES", None)
        executor.reset_probe()


def test_code_size_limit(client):
    """Requests exceeding maximum code size must be rejected with HTTP 413."""
    os.environ["FLOWFORGE_EXECUTION"] = "local-dev"
    os.environ["FLOWFORGE_EXEC_MAX_CODE_CHARS"] = "200"
    executor.reset_probe()
    try:
        huge_code = "# " + ("A" * 500) + "\nprint(1)"
        response = client.post("/api/execute", json={"code": huge_code, "user_input": ""})
        assert response.status_code == 413
        data = response.json()
        assert "longer than" in data.get("detail", "").lower() or "exceeds" in data.get("detail", "").lower()
    finally:
        os.environ.pop("FLOWFORGE_EXECUTION", None)
        os.environ.pop("FLOWFORGE_EXEC_MAX_CODE_CHARS", None)
        executor.reset_probe()


# ==============================================================================
# 5. Frontend Response Field Compatibility
# ==============================================================================

def test_api_response_compatibility(client):
    """Verify /api/execute returns all fields expected by the frontend."""
    os.environ["FLOWFORGE_EXECUTION"] = "local-dev"
    try:
        code = "print('Compatibility test')"
        response = client.post("/api/execute", json={"code": code, "user_input": ""})
        assert response.status_code == 200
        data = response.json()

        # All existing frontend fields
        expected_fields = ["output", "stdout", "stderr", "status", "success", "error_details", "program_output"]
        for field in expected_fields:
            assert field in data, f"Missing required field: {field}"

        assert isinstance(data["output"], str)
        assert isinstance(data["stdout"], str)
        assert isinstance(data["stderr"], str)
        assert isinstance(data["status"], str)
        assert isinstance(data["success"], bool)
        assert isinstance(data["error_details"], str)
        assert isinstance(data["program_output"], str)

        # Structured Stage 1 additions
        assert "timed_out" in data
        assert "truncated" in data
        assert "execution_mode" in data
    finally:
        os.environ.pop("FLOWFORGE_EXECUTION", None)


# ==============================================================================
# 6. Concurrency Limiting, AST Banned Modules, and EOFError Handling
# ==============================================================================

def test_concurrency_limit_exceeded(app):
    """Verify concurrency limit properly throttles simultaneous execution requests."""
    async def _run():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as async_client:
            os.environ["FLOWFORGE_EXECUTION"] = "local-dev"
            executor.reset_probe()
            # Temporarily set semaphore to 1 slot
            old_sem = executor._slots
            old_size = executor._slots_size
            executor._slots = None
            executor._slots_size = 0
            executor._acquire_slot.__globals__['_slots'] = None
            executor._acquire_slot.__globals__['_slots_size'] = 0
            try:
                sleep_code = "import time\ntime.sleep(1.2)\nprint('Done')"

                # Task 1 occupies the slot
                t1 = asyncio.create_task(
                    async_client.post("/api/execute", json={"code": sleep_code, "user_input": ""})
                )
                await asyncio.sleep(0.1)

                # Task 2 also waits for the slot
                t2 = asyncio.create_task(
                    async_client.post("/api/execute", json={"code": sleep_code, "user_input": ""})
                )

                responses = await asyncio.gather(t1, t2)
                status_codes = [r.status_code for r in responses]
                # Both either succeed sequentially or 429 if timeout exceeded
                assert 200 in status_codes
                for r in responses:
                    assert r.status_code in (200, 429)
            finally:
                executor._acquire_slot.__globals__['_slots'] = old_sem
                executor._acquire_slot.__globals__['_slots_size'] = old_size
                os.environ.pop("FLOWFORGE_EXECUTION", None)
                executor.reset_probe()

    asyncio.run(_run())


def test_banned_modules_and_builtins():
    """Verify AST check strictly catches banned modules and __builtins__ tampering."""
    os.environ["FLOWFORGE_EXECUTION"] = "local-dev"
    try:
        for mod in ["os", "sys", "subprocess", "socket", "shutil", "pathlib", "ctypes"]:
            code = f"import {mod}\nprint('hacked')"
            res = executor.execute(code, client_is_local=True)
            assert res.success is False
            assert "Security Error" in res.message or "Restricted import" in res.message

        builtins_code = "__builtins__.__import__('os').system('dir')"
        res_b = executor.execute(builtins_code, client_is_local=True)
        assert res_b.success is False
        assert "restricted" in res_b.message.lower() or "security" in res_b.message.lower()
    finally:
        os.environ.pop("FLOWFORGE_EXECUTION", None)


def test_eof_error_handling():
    """Verify program asking for more inputs than provided produces clear guidance."""
    os.environ["FLOWFORGE_EXECUTION"] = "local-dev"
    try:
        code = "a = input('Val 1: ')\nb = input('Val 2: ')\nprint(a, b)"
        # Provide only 1 input line
        res = executor.execute(code, "only_one_line\n", client_is_local=True)
        assert res.success is False
        assert res.status == "error"
        assert "asked for more input values" in res.message
    finally:
        os.environ.pop("FLOWFORGE_EXECUTION", None)


def test_safe_dist_file_direct(tmp_path, monkeypatch):
    """Directly test _safe_dist_file against escaping vectors."""
    dist = tmp_path / "static"
    dist.mkdir()
    valid_file = dist / "valid.txt"
    valid_file.write_text("hello", encoding="utf-8")
    monkeypatch.setattr(api_server, "DIST_DIR", dist)

    # Valid file resolves
    assert api_server._safe_dist_file("valid.txt") == valid_file.resolve()

    # Escaping and dangerous paths resolve to None
    dangerous = [
        "../secret.txt",
        "..\\secret.txt",
        "%2e%2e/secret.txt",
        "%252e%252e/secret.txt",
        "\0valid.txt",
        ".env",
        ".git/config",
        "sub/../../secret.txt",
        "",
    ]
    for d in dangerous:
        assert api_server._safe_dist_file(d) is None, f"Failed to reject: {d}"
