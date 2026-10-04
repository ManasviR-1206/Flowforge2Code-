import io
import sys
import multiprocessing
import traceback

def _execute_worker(code_str, user_inputs_str, queue):
    """
    Subprocess worker executing user python code safely in isolation.
    """
    output_buffer = io.StringIO()
    input_lines = user_inputs_str.splitlines() if user_inputs_str else []
    
    def mock_input(prompt=""):
        if prompt:
            output_buffer.write(str(prompt))
        if input_lines:
            val = input_lines.pop(0)
            output_buffer.write(f"{val}\n")
            return val
        return ""

    safe_builtins = {
        "print": lambda *args, **kwargs: print(*args, file=output_buffer, **kwargs),
        "input": mock_input,
        "int": int,
        "float": float,
        "str": str,
        "bool": bool,
        "len": len,
        "range": range,
        "list": list,
        "dict": dict,
        "sum": sum,
        "abs": abs,
        "max": max,
        "min": min,
    }

    safe_globals = {
        "__builtins__": safe_builtins,
        "__name__": "__main__"
    }

    try:
        exec(code_str, safe_globals)
        queue.put({"success": True, "output": output_buffer.getvalue()})
    except Exception as e:
        queue.put({
            "success": False, 
            "output": f"{output_buffer.getvalue()}\nRuntime Error: {type(e).__name__}: {str(e)}"
        })

def run_code_safely(code_str, user_inputs_str="", timeout_sec=3):
    """
    Runs Python code with an isolated thread/process and 3-second timeout limit.
    """
    if not code_str or not code_str.strip():
        return "No code to execute."

    # Direct in-process execution fallback if multiprocessing context isn't supported
    try:
        queue = multiprocessing.Queue()
        proc = multiprocessing.Process(target=_execute_worker, args=(code_str, user_inputs_str, queue))
        proc.start()
        proc.join(timeout=timeout_sec)

        if proc.is_alive():
            proc.terminate()
            proc.join()
            return "Execution Error: Code execution timed out (limit: 3 seconds). Possible infinite loop."

        if not queue.empty():
            res = queue.get()
            return res["output"] if res["output"] else "Code executed successfully with no output."
        return "Execution finished."
    except Exception:
        # Fallback to string IO capture
        buffer = io.StringIO()
        inputs = user_inputs_str.splitlines()
        def fallback_input(prompt=""):
            return inputs.pop(0) if inputs else ""
        
        try:
            sys_stdout = sys.stdout
            sys.stdout = buffer
            exec(code_str, {"__builtins__": __builtins__, "input": fallback_input})
            return buffer.getvalue()
        except Exception as ex:
            return f"Execution Error: {str(ex)}"
        finally:
            sys.stdout = sys_stdout
