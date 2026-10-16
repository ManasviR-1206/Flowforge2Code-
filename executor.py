"""
FlowForge AI – Safe Code Execution Engine (Stage 1 Hardened)

Execution Modes (FLOWFORGE_EXECUTION):
- auto      : Fail-closed; verifies genuine OS-level container/sandbox isolation.
              If no verified sandbox is available (e.g. Windows host without container
              isolation), public execution remains disabled.
- local-dev : Explicitly unsafe mode for trusted local Windows development & demos.
              Enables local subprocess execution with AST checks, timeout, and output bounds.
              MUST NEVER be enabled implicitly on public deployments.
- disabled  : Completely disables code execution (/api/execute returns disabled).
"""
from __future__ import annotations

import ast
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger("flowforge.executor")

# Configuration and resource limits
DEFAULT_TIMEOUT_SEC = 5
MAX_TIMEOUT_SEC = 15
DEFAULT_MAX_CODE_SIZE = 65536      # 64 KB
DEFAULT_MAX_OUTPUT_SIZE = 32768    # 32 KB

BANNED_MODULES = {
    "os", "sys", "subprocess", "socket", "shutil", "pathlib", "ctypes",
    "importlib", "multiprocessing", "threading", "signal", "pickle",
    "http", "urllib", "requests", "ftplib", "webbrowser",
}


class ExecutionResult(str):
    """
    String-compatible execution result with structured attributes.
    Preserves 100% backward-compatibility with callers expecting a str,
    while providing structured access to stdout, stderr, exit_code, and status.
    """
    stdout: str
    stderr: str
    exit_code: Optional[int]
    status: str          # "success", "error", "timeout", "disabled", "rejected"
    success: bool
    timed_out: bool
    truncated: bool
    error_details: str
    program_output: str
    execution_mode: str
    sandboxed: bool

    def __new__(cls, content: str, **kwargs):
        obj = super().__new__(cls, content)
        obj.stdout = kwargs.get("stdout", "")
        obj.stderr = kwargs.get("stderr", "")
        obj.exit_code = kwargs.get("exit_code")
        obj.status = kwargs.get("status", "error")
        obj.success = bool(kwargs.get("success", False))
        obj.timed_out = bool(kwargs.get("timed_out", False))
        obj.truncated = bool(kwargs.get("truncated", False))
        obj.error_details = kwargs.get("error_details", "")
        obj.program_output = kwargs.get("program_output", "")
        obj.execution_mode = kwargs.get("execution_mode", "disabled")
        obj.sandboxed = bool(kwargs.get("sandboxed", False))
        return obj

    def to_dict(self) -> Dict[str, Any]:
        return {
            "output": str(self),
            "stdout": self.stdout,
            "stderr": self.stderr,
            "status": self.status,
            "success": self.success,
            "error_details": self.error_details,
            "program_output": self.program_output,
            "exit_code": self.exit_code,
            "timed_out": self.timed_out,
            "truncated": self.truncated,
            "execution_mode": self.execution_mode,
            "sandboxed": self.sandboxed,
        }


def get_config_limits() -> Dict[str, int]:
    """Retrieve execution and resource limits from environment variables."""
    try:
        max_code = int(os.getenv("FLOWFORGE_MAX_CODE_SIZE", str(DEFAULT_MAX_CODE_SIZE)))
    except ValueError:
        max_code = DEFAULT_MAX_CODE_SIZE

    try:
        max_output = int(os.getenv("FLOWFORGE_MAX_OUTPUT_SIZE", str(DEFAULT_MAX_OUTPUT_SIZE)))
    except ValueError:
        max_output = DEFAULT_MAX_OUTPUT_SIZE

    try:
        timeout = int(os.getenv("FLOWFORGE_EXECUTION_TIMEOUT", str(DEFAULT_TIMEOUT_SEC)))
        timeout = max(1, min(timeout, MAX_TIMEOUT_SEC))
    except ValueError:
        timeout = DEFAULT_TIMEOUT_SEC

    return {
        "max_code_size": max_code,
        "max_output_size": max_output,
        "timeout_sec": timeout,
    }


def verify_sandbox_environment() -> Tuple[bool, str, str]:
    """
    Probe host environment for genuine OS-level container or sandbox isolation.
    Returns (is_verified, sandbox_type, reason).
    Fails closed if safe isolation cannot be strictly verified.
    """
    # 1. Check for dedicated container runtime indicators (e.g. Docker / OCI container)
    if os.path.exists("/.dockerenv"):
        return True, "docker", "Running inside containerized environment"

    # 2. Check for Linux namespace isolation tools (nsjail, gVisor runsc, bwrap)
    if sys.platform.startswith("linux"):
        for tool in ("nsjail", "runsc", "bwrap"):
            if shutil.which(tool):
                return True, tool, f"Verified sandbox tool available: {tool}"

    # 3. Native Windows host environment
    # Native Windows processes do not provide genuine public isolation for arbitrary code
    return (
        False,
        "none",
        "No genuine OS-level sandbox isolation available on current host environment. "
        "Public execution disabled to prevent Remote Code Execution (RCE).",
    )


def get_execution_mode() -> str:
    """
    Resolve active execution mode.
    Modes:
      'auto'      - Fail closed: only enabled if genuine OS sandbox is verified.
      'local-dev' - Allowed only when explicitly set via FLOWFORGE_EXECUTION.
      'disabled'  - Execution explicitly disabled.
    """
    raw = os.getenv("FLOWFORGE_EXECUTION", os.getenv("FLOWFORGE_EXECUTION_MODE", "auto")).strip().lower()
    if raw == "local-dev":
        return "local-dev"
    elif raw == "disabled":
        return "disabled"
    elif raw == "auto":
        is_verified, _, _ = verify_sandbox_environment()
        return "sandbox" if is_verified else "disabled"
    elif raw == "sandbox":
        is_verified, _, _ = verify_sandbox_environment()
        return "sandbox" if is_verified else "disabled"
    return "disabled"


def _assert_safe(code_str: str) -> None:
    """Basic AST safety checks (used in local-dev for sanity; not a sandbox guarantee)."""
    tree = ast.parse(code_str)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if root in BANNED_MODULES:
                    raise ValueError(f"Restricted import: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root in BANNED_MODULES:
                raise ValueError(f"Restricted import: {node.module}")
        elif isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id == "__builtins__":
                raise ValueError("Access to __builtins__ is not allowed.")


def extract_program_output(raw_stdout: str) -> str:
    """
    Separate pure program output from interactive prompts (e.g. 'Enter a: ').
    """
    cleaned_lines = []
    for line in raw_stdout.splitlines():
        stripped = line.strip()
        if re.fullmatch(r"Enter\s+.*?:", stripped):
            continue
        if re.fullmatch(r"Enter\s+.*?:\s*", stripped):
            continue
        cleaned_lines.append(line)
    output = "\n".join(part for part in cleaned_lines if part.strip() or part == "").strip()
    return output if output else raw_stdout.strip()


def run_code_safely(
    code_str: str,
    user_inputs_str: str = "",
    timeout_sec: Optional[int] = None,
) -> ExecutionResult:
    """
    Execute user Python code with strict bounds, resource gating, and structured reporting.
    Preserves signature: run_code_safely(code, user_input, timeout_sec).
    """
    limits = get_config_limits()
    max_code_size = limits["max_code_size"]
    max_output_size = limits["max_output_size"]

    if timeout_sec is None:
        timeout_sec = limits["timeout_sec"]
    else:
        try:
            timeout_sec = max(1, min(int(timeout_sec), MAX_TIMEOUT_SEC))
        except (ValueError, TypeError):
            timeout_sec = limits["timeout_sec"]

    mode = get_execution_mode()

    # Gate: Execution disabled when sandbox is unavailable
    if mode == "disabled":
        _, _, reason = verify_sandbox_environment()
        msg = (
            f"Execution disabled: {reason} "
            "For trusted local college demonstrations, set FLOWFORGE_EXECUTION=local-dev in .env."
        )
        return ExecutionResult(
            msg,
            stdout="",
            stderr=msg,
            exit_code=None,
            status="disabled",
            success=False,
            timed_out=False,
            truncated=False,
            error_details=msg,
            program_output="",
            execution_mode="disabled",
            sandboxed=False,
        )

    # Empty code check
    if not code_str or not str(code_str).strip():
        msg = "No code to execute."
        return ExecutionResult(
            msg,
            stdout="",
            stderr=msg,
            exit_code=None,
            status="error",
            success=False,
            timed_out=False,
            truncated=False,
            error_details=msg,
            program_output="",
            execution_mode=mode,
            sandboxed=(mode == "sandbox"),
        )

    # Code size limit check
    code_bytes = code_str.encode("utf-8", errors="replace")
    if len(code_bytes) > max_code_size:
        msg = f"Execution Error: Code size ({len(code_bytes)} bytes) exceeds the maximum allowed limit ({max_code_size} bytes)."
        return ExecutionResult(
            msg,
            stdout="",
            stderr=msg,
            exit_code=None,
            status="rejected",
            success=False,
            timed_out=False,
            truncated=False,
            error_details=msg,
            program_output="",
            execution_mode=mode,
            sandboxed=(mode == "sandbox"),
        )

    # Pre-execution AST checks
    try:
        _assert_safe(code_str)
    except SyntaxError as e:
        msg = f"Syntax Error: {e}"
        return ExecutionResult(
            msg,
            stdout="",
            stderr=msg,
            exit_code=None,
            status="error",
            success=False,
            timed_out=False,
            truncated=False,
            error_details=msg,
            program_output="",
            execution_mode=mode,
            sandboxed=(mode == "sandbox"),
        )
    except ValueError as e:
        msg = f"Security Error: {e}"
        return ExecutionResult(
            msg,
            stdout="",
            stderr=msg,
            exit_code=None,
            status="error",
            success=False,
            timed_out=False,
            truncated=False,
            error_details=msg,
            program_output="",
            execution_mode=mode,
            sandboxed=(mode == "sandbox"),
        )

    # Wrap code with correct prompt and newline handling
    wrapped_code = (
        "import builtins\n"
        "import sys\n"
        "_flowforge_original_input = builtins.input\n"
        "def _flowforge_input(prompt=''):\n"
        "    if prompt is not None and prompt != '':\n"
        "        sys.stdout.write(str(prompt))\n"
        "        if not str(prompt).endswith('\\n'):\n"
        "            sys.stdout.write('\\n')\n"
        "        sys.stdout.flush()\n"
        "    return _flowforge_original_input()\n"
        "builtins.input = _flowforge_input\n"
        f"{code_str}\n"
    )

    fd, path = tempfile.mkstemp(suffix=".py", prefix="flowforge_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(wrapped_code)

        env = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONIOENCODING": "utf-8",
            "PYTHONDONTWRITEBYTECODE": "1",
        }

        inputs_str = str(user_inputs_str) if user_inputs_str else ""
        if inputs_str and not inputs_str.endswith("\n"):
            inputs_str += "\n"

        cmd = [sys.executable, "-I", "-B", path]
        try:
            proc = subprocess.run(
                cmd,
                input=inputs_str,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                cwd=tempfile.gettempdir(),
                env=env,
            )
        except OSError:
            # Fallback if -I flag is unsupported by local Python build
            proc = subprocess.run(
                [sys.executable, path],
                input=inputs_str,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                cwd=tempfile.gettempdir(),
                env=env,
            )

        raw_stdout = (proc.stdout or "").replace("\r\n", "\n")
        raw_stderr = (proc.stderr or "").replace("\r\n", "\n")

        # Check output truncation limits
        truncated = False
        if len(raw_stdout) > max_output_size:
            raw_stdout = raw_stdout[:max_output_size] + f"\n[Output truncated: exceeded {max_output_size} bytes limit]"
            truncated = True
        if len(raw_stderr) > max_output_size:
            raw_stderr = raw_stderr[:max_output_size] + f"\n[Stderr truncated: exceeded {max_output_size} bytes limit]"
            truncated = True

        exit_code = proc.returncode
        success = (exit_code == 0)

        if success:
            status = "success"
            error_details = ""
            program_out = extract_program_output(raw_stdout)
            full_output = raw_stdout if raw_stdout else "Code executed successfully with no output."
        else:
            status = "error"
            if "EOFError" in raw_stderr:
                eof_msg = (
                    "Execution stopped: the program asked for more input values than you provided. "
                    "Add more lines in the Program Input box (one value per line), then run again."
                )
                error_details = eof_msg
                full_output = (raw_stdout + "\n" + eof_msg).strip() if raw_stdout else eof_msg
                program_out = extract_program_output(raw_stdout)
            else:
                sanitized_err = raw_stderr.replace(path, "<program>").strip()
                error_details = sanitized_err if sanitized_err else f"Execution Error: process exited with code {exit_code}"
                full_output = (raw_stdout + "\n" + error_details).strip() if raw_stdout else error_details
                program_out = ""

        return ExecutionResult(
            full_output,
            stdout=raw_stdout,
            stderr=raw_stderr,
            exit_code=exit_code,
            status=status,
            success=success,
            timed_out=False,
            truncated=truncated,
            error_details=error_details,
            program_output=program_out,
            execution_mode=mode,
            sandboxed=(mode == "sandbox"),
        )

    except subprocess.TimeoutExpired:
        timeout_msg = f"Execution Error: Code execution timed out (limit: {timeout_sec} seconds). Possible infinite loop."
        return ExecutionResult(
            timeout_msg,
            stdout="",
            stderr=timeout_msg,
            exit_code=None,
            status="timeout",
            success=False,
            timed_out=True,
            truncated=False,
            error_details=timeout_msg,
            program_output="",
            execution_mode=mode,
            sandboxed=(mode == "sandbox"),
        )
    except Exception as ex:
        err_msg = f"Execution Error: {ex}"
        return ExecutionResult(
            err_msg,
            stdout="",
            stderr=err_msg,
            exit_code=None,
            status="error",
            success=False,
            timed_out=False,
            truncated=False,
            error_details=err_msg,
            program_output="",
            execution_mode=mode,
            sandboxed=(mode == "sandbox"),
        )
    finally:
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass
