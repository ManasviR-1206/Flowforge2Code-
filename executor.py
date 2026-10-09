import ast
import os
import re
import subprocess
import sys
import tempfile

BANNED_MODULES = {
    "os", "sys", "subprocess", "socket", "shutil", "pathlib", "ctypes",
    "importlib", "multiprocessing", "threading", "signal", "pickle",
    "http", "urllib", "requests", "ftplib", "webbrowser",
}


def _assert_safe(code_str: str) -> None:
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


def run_code_safely(code_str, user_inputs_str="", timeout_sec=5):
    if not code_str or not str(code_str).strip():
        return "No code to execute."

    try:
        _assert_safe(code_str)
    except SyntaxError as e:
        return f"Syntax Error: {e}"
    except ValueError as e:
        return f"Security Error: {e}"

    wrapped_code = (
        "import builtins\n"
        "import sys\n"
        "_flowforge_original_input = builtins.input\n"
        "def _flowforge_input(prompt=''):\n"
        "    if prompt is not None:\n"
        "        sys.stdout.write(str(prompt).rstrip() + '\\\n')\n"
        "        sys.stdout.flush()\n"
        "    return _flowforge_original_input()\n"
        "builtins.input = _flowforge_input\n"
        f"{code_str}"
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
        cmd = [sys.executable, "-I", path]
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
            proc = subprocess.run(
                [sys.executable, path],
                input=inputs_str,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                cwd=tempfile.gettempdir(),
                env=env,
            )
        out = (proc.stdout or "").replace("\r\n", "\n")
        err = (proc.stderr or "").replace("\r\n", "\n")
        out = re.sub(r"(?<!\n)(Enter\s+[^\n]*?:\s*)(?=Enter\s+|\S|$)", lambda m: m.group(1) + "\n", out)
        if proc.returncode != 0:
            if "EOFError" in err:
                return (
                    out
                    + "\nExecution stopped: the program asked for more input values "
                    + "than you provided. Add more lines in the Program Input box "
                    + "(one value per line), then run again."
                ).strip()
            if err:
                return (out + err.replace(path, "<program>")).strip()
            return f"Execution Error: process exited with code {proc.returncode}"
        return out if out else "Code executed successfully with no output."
    except subprocess.TimeoutExpired:
        return f"Execution Error: Code execution timed out (limit: {timeout_sec} seconds). Possible infinite loop."
    except Exception as ex:
        return f"Execution Error: {ex}"
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
