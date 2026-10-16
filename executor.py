"""
FlowForge Python execution.

SECURITY MODEL - read this before changing anything.

Running code that a stranger wrote is dangerous. The only thing in this module
that is allowed to be called a security boundary is the OS-level sandbox
(bubblewrap: separate user / PID / IPC / UTS / network namespaces, a minimal
read-only root, no capabilities, no nested user namespaces, tmpfs-only scratch
space).  Everything else (the AST check, rlimits, timeouts, output caps) is
defence in depth and is NOT sufficient on its own.

Execution is controlled by the FLOWFORGE_EXECUTION environment variable:

  auto       (default) Execute only if the sandbox backend is available AND a
                       start-up self-test proves its restrictions are really in
                       force on this host.  Otherwise execution is DISABLED
                       with a clear reason ("fail closed").
  sandbox    Same behaviour as auto, but states the intent explicitly.
  local-dev  EXPLICITLY UNSAFE.  Runs code in a plain subprocess with rlimits
                       (POSIX) and a timeout.  There is no isolation: the code
                       can read your files and use your network.  Intended only
                       for a demo on your own machine (e.g. Windows, where the
                       sandbox is unavailable).  It is never selected
                       implicitly, and the API only honours it for requests
                       coming from the same machine.
  off        Execution is disabled.

Any other value disables execution.
"""

from __future__ import annotations

import ast
import json
import logging
import math
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, Optional

log = logging.getLogger("flowforge.executor")

MODES = ("auto", "sandbox", "local-dev", "off")
DEFAULT_MODE = "auto"

# ---------------------------------------------------------------------------
# Static restrictions: DEFENCE IN DEPTH ONLY. These are trivially bypassable by
# a determined attacker and must never be relied upon as the security boundary.
# ---------------------------------------------------------------------------
BANNED_MODULES = {
    "os", "sys", "subprocess", "socket", "shutil", "pathlib", "ctypes",
    "importlib", "multiprocessing", "threading", "signal", "pickle",
    "http", "urllib", "requests", "ftplib", "webbrowser",
    # added in Stage 1
    "builtins", "runpy", "code", "codeop", "inspect", "gc", "marshal",
    "resource", "mmap", "fcntl", "posix", "nt", "pty", "tempfile", "glob",
    "asyncio", "select", "selectors", "atexit",
}
BANNED_NAMES = {
    "__import__", "eval", "exec", "compile", "open", "breakpoint", "globals",
    "locals", "vars", "getattr", "setattr", "delattr",
    "__builtins__", "__loader__", "__spec__",
}


def _assert_safe(code_str: str) -> None:
    """Raise SyntaxError / ValueError for code the static checks reject."""
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
        elif isinstance(node, ast.Name):
            if node.id in BANNED_NAMES:
                raise ValueError(f"Restricted name: {node.id}")
        elif isinstance(node, ast.Attribute):
            attr = node.attr
            if attr in BANNED_NAMES or (attr.startswith("__") and attr.endswith("__")):
                raise ValueError(f"Restricted attribute: {attr}")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Limits:
    timeout: float        # wall-clock seconds
    memory_mb: int        # RLIMIT_AS
    max_output: int       # bytes kept per stream; exceeding it stops the program
    max_code_chars: int
    max_input_chars: int
    max_concurrent: int   # simultaneous executions; more are refused (HTTP 429)
    tmpfs_mb: int         # size of the sandbox scratch /tmp
    fsize_mb: int         # RLIMIT_FSIZE (largest single file)
    nofile: int           # RLIMIT_NOFILE
    nproc: int            # RLIMIT_NPROC (sandbox only; see _probe_sandbox)


def _env_number(name: str, default, minimum, maximum, cast=int):
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = cast(raw)
    except ValueError:
        log.warning("Ignoring invalid %s=%r", name, raw)
        return default
    return max(minimum, min(maximum, value))


def get_limits() -> Limits:
    return Limits(
        timeout=_env_number("FLOWFORGE_EXEC_TIMEOUT", 5.0, 1.0, 30.0, float),
        memory_mb=_env_number("FLOWFORGE_EXEC_MEMORY_MB", 256, 64, 2048),
        max_output=_env_number("FLOWFORGE_EXEC_MAX_OUTPUT_BYTES", 65536, 1024, 1_048_576),
        max_code_chars=_env_number("FLOWFORGE_EXEC_MAX_CODE_CHARS", 20000, 100, 200_000),
        max_input_chars=_env_number("FLOWFORGE_EXEC_MAX_INPUT_CHARS", 4000, 0, 100_000),
        max_concurrent=_env_number("FLOWFORGE_EXEC_MAX_CONCURRENT", 2, 1, 32),
        tmpfs_mb=_env_number("FLOWFORGE_EXEC_TMPFS_MB", 8, 1, 256),
        fsize_mb=1,
        nofile=64,
        nproc=_env_number("FLOWFORGE_EXEC_MAX_PROCS", 16, 4, 256),
    )


def configured_mode() -> tuple[str, Optional[str]]:
    """Return (mode, problem). An unrecognised value yields ('off', explanation)."""
    raw = os.environ.get("FLOWFORGE_EXECUTION", "").strip().lower() or DEFAULT_MODE
    if raw not in MODES:
        return "off", f"Unrecognised FLOWFORGE_EXECUTION value {raw!r}; execution is disabled."
    return raw, None


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------
@dataclass
class ExecResult:
    status: str                      # success | error | timeout | rejected | too_large | disabled | busy
    stdout: str = ""
    stderr: str = ""
    exit_code: Optional[int] = None
    timed_out: bool = False
    truncated: bool = False
    leaked_processes: bool = False
    mode: str = ""
    message: str = ""                # human readable error text ("" on success)

    @property
    def success(self) -> bool:
        return self.status == "success"

    def legacy_output(self) -> str:
        """The single string the original run_code_safely() returned."""
        if self.status == "success":
            return self.stdout if self.stdout else "Code executed successfully with no output."
        return self.message


TIMEOUT_TEXT = "Execution Error: Code execution timed out (limit: {t:g} seconds). Possible infinite loop."
EOF_TEXT = (
    "\nExecution stopped: the program asked for more input values "
    "than you provided. Add more lines in the Program Input box "
    "(one value per line), then run again."
)
SIGNAL_TEXT = {
    137: "Execution Error: the program was killed (it probably exceeded the memory limit).",
    152: "Execution Error: CPU time limit exceeded.",
    153: "Execution Error: the program tried to write a file larger than the limit.",
}


# ---------------------------------------------------------------------------
# The launcher runs INSIDE the sandbox (or the local-dev subprocess). It applies
# resource limits before any user code runs, makes input() echo its prompt on its
# own line, and prints clean tracebacks. (The original wrapper used the escape
# '\\\n' which produced a line continuation, so prompts had no newline and a
# regex tried to repair the output afterwards.)
# ---------------------------------------------------------------------------
LAUNCHER = r'''
import builtins, json, linecache, sys, traceback

_cfg = json.loads(sys.argv[1])

try:
    import resource
except ImportError:
    resource = None

if resource is not None:
    for _name, _value in (
        ("RLIMIT_CORE", 0),
        ("RLIMIT_CPU", _cfg.get("cpu")),
        ("RLIMIT_AS", _cfg.get("as")),
        ("RLIMIT_FSIZE", _cfg.get("fsize")),
        ("RLIMIT_NOFILE", _cfg.get("nofile")),
        ("RLIMIT_NPROC", _cfg.get("nproc")),
    ):
        if _value is None or not hasattr(resource, _name):
            continue
        try:
            resource.setrlimit(getattr(resource, _name), (_value, _value))
        except (ValueError, OSError) as _exc:
            if _cfg.get("strict"):
                sys.stderr.write("FlowForge sandbox error: could not apply %s: %s\n" % (_name, _exc))
                sys.exit(97)

_original_input = builtins.input


def _flowforge_input(prompt=""):
    text = "" if prompt is None else str(prompt)
    if text:
        sys.stdout.write(text.rstrip() + "\n")
        sys.stdout.flush()
    return _original_input()


builtins.input = _flowforge_input

with open(_cfg["main"], encoding="utf-8") as _fh:
    _src = _fh.read()
linecache.cache["<program>"] = (len(_src), None, _src.splitlines(True), "<program>")
_globals = {"__name__": "__main__", "__builtins__": builtins}
try:
    exec(compile(_src, "<program>", "exec"), _globals)
except SystemExit:
    raise
except BaseException:
    _t, _v, _tb = sys.exc_info()
    traceback.print_exception(_t, _v, _tb.tb_next if _tb else None)
    sys.stdout.flush()
    sys.exit(1)
'''


# ---------------------------------------------------------------------------
# Process runner (shared by the sandbox and local-dev paths)
# ---------------------------------------------------------------------------
def _kill_tree(proc: subprocess.Popen) -> None:
    try:
        if os.name == "posix":
            os.killpg(proc.pid, signal.SIGKILL)
        else:  # pragma: no cover - Windows
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           capture_output=True, timeout=5)
    except (ProcessLookupError, PermissionError, OSError, subprocess.SubprocessError):
        try:
            proc.kill()
        except OSError:
            pass


def _read_stream(stream, cap: int, sink: bytearray, overflow: threading.Event) -> None:
    try:
        while True:
            chunk = stream.read1(65536)
            if not chunk:
                return
            room = cap - len(sink)
            if room > 0:
                sink.extend(chunk[:room])
            if len(chunk) > room:
                overflow.set()
    except (OSError, ValueError):
        return


def _feed_stdin(stream, data: bytes) -> None:
    try:
        stream.write(data)
        stream.flush()
    except (OSError, ValueError):
        pass
    finally:
        try:
            stream.close()
        except Exception:
            pass


def _processes_matching(marker: str) -> bool:
    """True if any live process has `marker` in its command line (Linux only)."""
    if not sys.platform.startswith("linux"):
        return False
    needle = marker.encode()
    me = str(os.getpid())
    try:
        for entry in os.listdir("/proc"):
            if not entry.isdigit() or entry == me:
                continue
            try:
                with open(f"/proc/{entry}/cmdline", "rb") as fh:
                    if needle in fh.read():
                        return True
            except OSError:
                continue
    except OSError:
        return False
    return False


def _run_process(argv, env, cwd, stdin_text: str, timeout: float, max_output: int, marker: str):
    """Run argv; return (stdout, stderr, returncode, timed_out, overflowed, truncated, leaked)."""
    proc = subprocess.Popen(
        argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        cwd=cwd, env=env, close_fds=True,
        start_new_session=(os.name == "posix"),
    )
    out, err = bytearray(), bytearray()
    overflow = threading.Event()
    threads = [
        threading.Thread(target=_read_stream, args=(proc.stdout, max_output, out, overflow), daemon=True),
        threading.Thread(target=_read_stream, args=(proc.stderr, max_output, err, overflow), daemon=True),
        threading.Thread(target=_feed_stdin, args=(proc.stdin, stdin_text.encode("utf-8", "replace")), daemon=True),
    ]
    for t in threads:
        t.start()

    deadline = time.monotonic() + timeout
    timed_out = overflowed = False
    while proc.poll() is None:
        if overflow.is_set():
            overflowed = True
            _kill_tree(proc)
            break
        if time.monotonic() >= deadline:
            timed_out = True
            _kill_tree(proc)
            break
        time.sleep(0.01)
    proc.wait()
    for t in threads:
        t.join(timeout=2)

    leaked = False
    if timed_out or overflowed:
        # Give the kernel a moment, then make sure nothing from this run survived.
        for _ in range(100):
            if not _processes_matching(marker):
                break
            time.sleep(0.01)
        else:
            leaked = True
            log.error("Processes from run %s survived the kill", marker)
    return bytes(out), bytes(err), proc.returncode, timed_out, overflowed, overflow.is_set(), leaked


def _decode(raw: bytes) -> str:
    return raw.decode("utf-8", "replace").replace("\r\n", "\n")


def _build_result(mode, out_b, err_b, rc, timed_out, overflowed, truncated, leaked, lim: Limits) -> ExecResult:
    out, err = _decode(out_b), _decode(err_b)
    if truncated:
        out += "\n[output truncated]"
    res = ExecResult(status="error", stdout=out, stderr=err, exit_code=rc, timed_out=timed_out,
                     truncated=truncated, leaked_processes=leaked, mode=mode)
    if timed_out:
        res.status = "timeout"
        res.message = TIMEOUT_TEXT.format(t=lim.timeout)
    elif overflowed:
        res.message = (f"Execution Error: the program printed more than "
                       f"{lim.max_output // 1024} KB of output and was stopped.")
    elif rc == 0:
        res.status = "success"
    elif "EOFError" in err:
        res.message = (out + EOF_TEXT).strip()
    elif rc in SIGNAL_TEXT or (rc is not None and rc < 0 and (128 - rc) in SIGNAL_TEXT):
        res.message = SIGNAL_TEXT[rc if rc in SIGNAL_TEXT else 128 - rc]
    elif err.strip():
        res.message = (out + err).strip()
    else:
        res.message = f"Execution Error: process exited with code {rc}"
    return res


def _write_workdir(code: str) -> str:
    workdir = tempfile.mkdtemp(prefix="ffexec_")
    os.chmod(workdir, 0o755)
    for name, body in (("launcher.py", LAUNCHER), ("main.py", code)):
        path = os.path.join(workdir, name)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(body)
        os.chmod(path, 0o644)
    return workdir


def _extra_runtime_prefixes(py: str) -> list[str]:
    """Interpreter prefixes living outside /usr that the sandbox must also mount."""
    extras = []
    for p in {sys.base_prefix, sys.base_exec_prefix, os.path.dirname(os.path.dirname(py))}:
        p = os.path.realpath(p)
        if p in ("/", "") or p == "/usr" or p.startswith("/usr/") or not os.path.isdir(p):
            continue
        extras.append(p)
    return sorted(extras)


def _bwrap_argv(bwrap: str, workdir: str, lim: Limits, py: str, cfg_json: str) -> list[str]:
    a = [
        bwrap,
        "--unshare-user", "--unshare-ipc", "--unshare-pid", "--unshare-net",
        "--unshare-uts", "--unshare-cgroup-try",
        "--disable-userns",              # no nested user namespaces inside the sandbox
        "--die-with-parent", "--new-session",
        "--cap-drop", "ALL",
        "--hostname", "flowforge-sandbox",
        "--ro-bind", "/usr", "/usr",
    ]
    for d in ("/lib", "/lib64", "/bin", "/sbin"):
        if os.path.islink(d):
            a += ["--symlink", os.readlink(d), d]
        elif os.path.isdir(d):
            a += ["--ro-bind", d, d]
    for extra in _extra_runtime_prefixes(py):
        a += ["--ro-bind", extra, extra]
    a += [
        "--proc", "/proc", "--dev", "/dev",
        "--size", str(lim.tmpfs_mb * 1024 * 1024), "--tmpfs", "/tmp",
        "--ro-bind", workdir, "/prog",
        # bubblewrap's root and /dev are writable, uncapped tmpfs mounts by default (found by
        # the self-test). Make everything read-only except the size-capped /tmp.
        "--remount-ro", "/dev", "--remount-ro", "/",
        "--chdir", "/tmp",
        "--clearenv",
        "--setenv", "PATH", "/usr/bin:/bin",
        "--setenv", "LANG", "C.UTF-8",
        "--setenv", "HOME", "/tmp",
        "--setenv", "PYTHONIOENCODING", "utf-8",
        "--setenv", "PYTHONDONTWRITEBYTECODE", "1",
        "--", py, "-I", "-u", "/prog/launcher.py", cfg_json,
    ]
    return a


def _run_program(code: str, user_input: str, lim: Limits, timeout: float, *,
                 sandboxed: bool, extra_env: Optional[dict] = None,
                 stdin_override: Optional[str] = None) -> ExecResult:
    """Run `code` once. Performs NO policy checks: callers must have done them."""
    stdin_text = stdin_override if stdin_override is not None else user_input
    if stdin_text and not stdin_text.endswith("\n"):
        stdin_text += "\n"
    run_id = uuid.uuid4().hex
    workdir = _write_workdir(code)
    cpu = int(math.ceil(timeout)) + 1
    cfg = {
        "run_id": run_id, "cpu": cpu, "as": lim.memory_mb * 1024 * 1024,
        "fsize": lim.fsize_mb * 1024 * 1024, "nofile": lim.nofile,
    }
    try:
        if sandboxed:
            bwrap = shutil.which("bwrap")
            if not bwrap:
                return ExecResult(status="error", mode="sandbox",
                                  message="Execution Error: the sandbox (bubblewrap) is not available.")
            cfg.update(main="/prog/main.py", nproc=lim.nproc, strict=True)
            py = os.path.realpath(sys.executable)
            argv = _bwrap_argv(bwrap, workdir, lim, py, json.dumps(cfg))
            env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin")}
            env.update(extra_env or {})
            cwd = None
            mode = "sandbox"
        else:
            cfg.update(main=os.path.join(workdir, "main.py"), nproc=None, strict=False)
            argv = [sys.executable, "-I", "-u", os.path.join(workdir, "launcher.py"), json.dumps(cfg)]
            env = {"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8",
                   "PYTHONDONTWRITEBYTECODE": "1"}
            for key in ("SYSTEMROOT", "WINDIR", "TEMP", "TMP"):  # Windows needs these to start Python
                if os.environ.get(key):
                    env[key] = os.environ[key]
            env.update(extra_env or {})
            cwd = workdir
            mode = "local-dev"
        try:
            parts = _run_process(argv, env, cwd, stdin_text, timeout, lim.max_output, run_id)
        except OSError as exc:
            return ExecResult(status="error", mode=mode,
                              message=f"Execution Error: could not start the interpreter ({exc.strerror or exc}).")
        return _build_result(mode, *parts, lim)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Sandbox self-test. Execution in auto/sandbox mode is enabled ONLY if every
# one of these checks passes on this host.
# ---------------------------------------------------------------------------
PROBE_PROGRAM = r'''
import ctypes, json, os, resource, socket, sys, time
p = json.loads(sys.stdin.read())
r = {}
r["env_clean"] = "FLOWFORGE_PROBE_SECRET" not in os.environ and "GEMINI_API_KEY" not in os.environ
r["host_file_hidden"] = not os.path.exists(p["canary"])
r["minimal_root"] = set(os.listdir("/")) <= {"usr", "lib", "lib64", "bin", "sbin", "proc", "dev", "tmp", "prog"}

def writable(path):
    try:
        with open(path, "w") as fh:
            fh.write("x")
        return True
    except OSError:
        return False

r["system_readonly"] = not any(writable(x) for x in (
    "/usr/ffprobe", "/ffprobe", "/prog/ffprobe", "/dev/ffprobe", "/dev/shm/ffprobe", "/bin/ffprobe"))

total = 0
try:
    for i in range(10000):
        with open("/tmp/f%d" % i, "wb") as fh:
            fh.write(b"x" * 262144)
        total += 262144
        if total > p["tmpfs_bytes"] * 4:
            break
except OSError:
    pass
r["tmpfs_capped"] = total <= p["tmpfs_bytes"]

s = socket.socket()
s.settimeout(2)
try:
    s.connect(("127.0.0.1", p["port"]))
    r["network_blocked"] = False
except OSError:
    r["network_blocked"] = True
finally:
    s.close()
r["loopback_only"] = [l.split(":")[0].strip() for l in open("/proc/net/dev").read().splitlines()[2:]] == ["lo"]

try:
    bytearray(p["mem_bytes"] * 2)
    r["memory_limited"] = False
except MemoryError:
    r["memory_limited"] = True

kids, failed = [], False
try:
    for _ in range(200):
        pid = os.fork()
        if pid == 0:
            time.sleep(3)
            os._exit(0)
        kids.append(pid)
except OSError:
    failed = True
for k in kids:
    try:
        os.kill(k, 9)
    except OSError:
        pass
for k in kids:
    try:
        os.waitpid(k, 0)
    except OSError:
        pass
r["process_limited"] = failed

libc = ctypes.CDLL(None, use_errno=True)
r["nested_userns_blocked"] = libc.unshare(0x10000000) == -1
status = open("/proc/self/status").read().splitlines()
r["no_capabilities"] = [l.split()[1] for l in status if l.startswith("CapEff")] == ["0000000000000000"]
r["no_new_privs"] = [l.split()[1] for l in status if l.startswith("NoNewPrivs")] == ["1"]
r["pid_namespace"] = len([d for d in os.listdir("/proc") if d.isdigit()]) < 20
r["rlimits_applied"] = all(getattr(resource, n) is not None and resource.getrlimit(getattr(resource, n))[1] == v
                           for n, v in p["expect_rlimits"].items())
print(json.dumps(r))
'''

_PROBE_REQUIRED = (
    "env_clean", "host_file_hidden", "minimal_root", "system_readonly", "tmpfs_capped",
    "network_blocked", "loopback_only", "memory_limited", "process_limited",
    "nested_userns_blocked", "no_capabilities", "no_new_privs", "pid_namespace",
    "rlimits_applied", "timeout_kill", "output_cap", "no_leaked_processes",
)

_probe_lock = threading.Lock()
_probe_cache: Optional[dict] = None
_warming = False


def _probe_sandbox() -> dict:
    out: dict[str, Any] = {"ready": False, "reason": "", "backend": "", "verified": {}}
    if not sys.platform.startswith("linux"):
        out["reason"] = "The execution sandbox requires Linux; it is not available on this platform."
        return out
    bwrap = shutil.which("bwrap")
    if not bwrap:
        out["reason"] = "The execution sandbox (bubblewrap, 'bwrap') is not installed."
        return out
    try:
        out["backend"] = subprocess.run([bwrap, "--version"], capture_output=True, text=True,
                                        timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        out["reason"] = "bubblewrap could not be executed."
        return out

    lim = get_limits()
    verified: dict[str, bool] = {}
    canary_fd, canary = tempfile.mkstemp(prefix="ffcanary_")
    listener = socket.socket()
    try:
        os.write(canary_fd, b"host secret canary")
        os.close(canary_fd)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        listener.settimeout(0)
        probe_input = json.dumps({
            "canary": canary, "port": listener.getsockname()[1],
            "tmpfs_bytes": lim.tmpfs_mb * 1024 * 1024, "mem_bytes": lim.memory_mb * 1024 * 1024,
            "expect_rlimits": {
                "RLIMIT_AS": lim.memory_mb * 1024 * 1024, "RLIMIT_FSIZE": lim.fsize_mb * 1024 * 1024,
                "RLIMIT_NOFILE": lim.nofile, "RLIMIT_NPROC": lim.nproc, "RLIMIT_CORE": 0,
                "RLIMIT_CPU": int(math.ceil(8)) + 1,
            },
        })
        # Secrets are deliberately placed in the environment of the bwrap process
        # so the test proves --clearenv really strips them.
        res = _run_program(PROBE_PROGRAM, "", lim, 8, sandboxed=True, stdin_override=probe_input,
                           extra_env={"FLOWFORGE_PROBE_SECRET": "x", "GEMINI_API_KEY": "probe"})
        inner: dict = {}
        if res.status == "success":
            try:
                inner = json.loads(res.stdout.strip().splitlines()[-1])
            except (ValueError, IndexError):
                inner = {}
        verified.update({k: bool(inner.get(k)) for k in _PROBE_REQUIRED
                         if k not in ("timeout_kill", "output_cap", "no_leaked_processes")})
        try:  # belt and braces: did the sandboxed program actually reach our listener?
            listener.accept()
            verified["network_blocked"] = False
        except (BlockingIOError, OSError):
            pass
        if res.status != "success":
            out["reason"] = ("Sandbox self-test could not run: "
                             + (res.message or "unknown error")[:300])

        t0 = time.monotonic()
        spin = _run_program("while True:\n    pass\n", "", lim, 1, sandboxed=True)
        verified["timeout_kill"] = spin.timed_out and (time.monotonic() - t0) < 5
        leaked = spin.leaked_processes
        flood = _run_program("while True:\n    print('x' * 1000)\n", "", lim, 5, sandboxed=True)
        verified["output_cap"] = flood.truncated and not flood.success
        leaked = leaked or flood.leaked_processes
        verified["no_leaked_processes"] = not leaked
    except Exception as exc:  # any surprise => fail closed
        log.exception("Sandbox self-test crashed")
        out["reason"] = f"Sandbox self-test crashed: {exc}"
    finally:
        listener.close()
        try:
            os.unlink(canary)
        except OSError:
            pass

    verified = {k: bool(verified.get(k)) for k in _PROBE_REQUIRED}
    out["verified"] = verified
    failed = [k for k, ok in verified.items() if not ok]
    if failed:
        hint = ""
        if "process_limited" in failed and hasattr(os, "geteuid") and os.geteuid() == 0:
            hint = " (the server is running as root, for which the kernel does not enforce the " \
                   "process limit; run the server as a non-root user)"
        out["reason"] = out["reason"] or ("Sandbox self-test failed: " + ", ".join(failed) + hint)
        out["ready"] = False
    else:
        out["ready"] = True
        out["reason"] = ""
    return out


def sandbox_probe(block: bool = True, force: bool = False) -> Optional[dict]:
    """Run (or return the cached result of) the sandbox self-test."""
    global _probe_cache
    if _probe_cache is not None and not force:
        return _probe_cache
    if not block:
        warm_up()
        return None
    with _probe_lock:
        if _probe_cache is None or force:
            _probe_cache = _probe_sandbox()
            if _probe_cache["ready"]:
                log.info("Execution sandbox verified (%s).", _probe_cache["backend"])
            else:
                log.warning("Execution sandbox NOT available: %s", _probe_cache["reason"])
        return _probe_cache


def warm_up() -> None:
    """Start the sandbox self-test in the background (called at application start-up)."""
    global _warming
    mode, _ = configured_mode()
    if mode not in ("auto", "sandbox") or _probe_cache is not None or _warming:
        return
    _warming = True

    def _work():
        global _warming
        try:
            sandbox_probe(block=True)
        finally:
            _warming = False

    threading.Thread(target=_work, name="flowforge-sandbox-probe", daemon=True).start()


def reset_probe() -> None:
    """Forget the cached self-test result (used by tests)."""
    global _probe_cache
    with _probe_lock:
        _probe_cache = None


def execution_status(block: bool = True) -> dict:
    """Public, non-sensitive description of whether execution is enabled and why not."""
    mode, problem = configured_mode()
    if problem:
        return {"mode": "off", "enabled": False, "isolated": False, "state": "disabled", "reason": problem}
    if mode == "off":
        return {"mode": "off", "enabled": False, "isolated": False, "state": "disabled",
                "reason": "Code execution is disabled (FLOWFORGE_EXECUTION=off)."}
    if mode == "local-dev":
        return {"mode": "local-dev", "enabled": True, "isolated": False, "state": "ready", "reason": "",
                "warning": "UNSAFE local-dev mode: no isolation. Only for use on your own machine."}
    probe = sandbox_probe(block=block)
    if probe is None:
        return {"mode": mode, "enabled": False, "isolated": False, "state": "checking",
                "reason": "Checking sandbox availability..."}
    if probe["ready"]:
        return {"mode": mode, "enabled": True, "isolated": True, "state": "ready", "reason": "",
                "backend": probe["backend"]}
    return {"mode": mode, "enabled": False, "isolated": False, "state": "unavailable",
            "reason": "Code execution is disabled: " + probe["reason"]}


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------
_slot_lock = threading.Lock()
_slots: Optional[threading.BoundedSemaphore] = None
_slots_size = 0


def _acquire_slot() -> Optional[threading.BoundedSemaphore]:
    global _slots, _slots_size
    size = get_limits().max_concurrent
    with _slot_lock:
        if _slots is None or _slots_size != size:
            _slots, _slots_size = threading.BoundedSemaphore(size), size
        sem = _slots
    return sem if sem.acquire(blocking=False) else None


def execute(code: Any, user_input: Any = "", timeout_sec: Optional[float] = None,
            client_is_local: bool = True) -> ExecResult:
    """Validate, apply policy, and run `code`. Never raises for bad input."""
    status = execution_status(block=True)
    mode = status["mode"]
    if not status["enabled"]:
        return ExecResult(status="disabled", mode=mode, message=status["reason"])
    if mode == "local-dev" and not client_is_local:
        return ExecResult(
            status="disabled", mode=mode,
            message="Code execution is disabled: the unsafe local-dev mode only accepts requests "
                    "made from the same machine.")

    lim = get_limits()
    code = "" if code is None else str(code)
    user_input = "" if user_input is None else str(user_input)
    if not code.strip():
        return ExecResult(status="rejected", mode=mode, message="No code to execute.")
    if len(code) > lim.max_code_chars or "\x00" in code:
        return ExecResult(status="too_large", mode=mode,
                          message=f"Execution Error: code is longer than {lim.max_code_chars} characters.")
    if len(user_input) > lim.max_input_chars or "\x00" in user_input:
        return ExecResult(status="too_large", mode=mode,
                          message=f"Execution Error: program input is longer than {lim.max_input_chars} characters.")
    try:
        _assert_safe(code)
    except SyntaxError as exc:
        return ExecResult(status="rejected", mode=mode, message=f"Syntax Error: {exc}")
    except ValueError as exc:
        return ExecResult(status="rejected", mode=mode, message=f"Security Error: {exc}")

    timeout = lim.timeout if timeout_sec is None else max(0.5, min(float(timeout_sec), lim.timeout))
    sem = _acquire_slot()
    if sem is None:
        return ExecResult(status="busy", mode=mode,
                          message="The server is busy running other programs. Try again in a moment.")
    try:
        return _run_program(code, user_input, lim, timeout, sandboxed=(mode != "local-dev"))
    finally:
        sem.release()


def run_code_safely(code_str, user_inputs_str="", timeout_sec=5):
    """Backwards-compatible wrapper returning the single output string."""
    return execute(code_str, user_inputs_str, timeout_sec).legacy_output()
