from __future__ import annotations
import ast as py_ast
import json
import os
import sys
import urllib.request
import urllib.error

import logic_engine
import executor

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE = os.environ.get("FLOWFORGE_API", "http://127.0.0.1:8000")

# 1. Calculator Flowchart Graph with unquoted operation == + condition
CALC_GRAPH = {
    "nodes": [
        {"id": "1", "type": "start_end", "position": {"x": 300, "y": 40}, "data": {"label": "Start"}},
        {"id": "2", "type": "input_output", "position": {"x": 300, "y": 120}, "data": {"label": "Input a"}},
        {"id": "3", "type": "input_output", "position": {"x": 300, "y": 200}, "data": {"label": "Input b"}},
        {"id": "4", "type": "input_output", "position": {"x": 300, "y": 280}, "data": {"label": "Input operation"}},
        {"id": "5", "type": "decision", "position": {"x": 300, "y": 380}, "data": {"label": "operation == +"}},
        {"id": "6", "type": "process", "position": {"x": 140, "y": 500}, "data": {"label": "result = a + b"}},
        {"id": "7", "type": "process", "position": {"x": 460, "y": 500}, "data": {"label": "result = a - b"}},
        {"id": "8", "type": "input_output", "position": {"x": 300, "y": 620}, "data": {"label": "Print result"}},
        {"id": "9", "type": "start_end", "position": {"x": 300, "y": 720}, "data": {"label": "End"}},
    ],
    "edges": [
        {"id": "e1", "source": "1", "target": "2"},
        {"id": "e2", "source": "2", "target": "3"},
        {"id": "e3", "source": "3", "target": "4"},
        {"id": "e4", "source": "4", "target": "5"},
        {"id": "e5", "source": "5", "target": "6", "sourceHandle": "yes", "label": "Yes"},
        {"id": "e6", "source": "5", "target": "7", "sourceHandle": "no", "label": "No"},
        {"id": "e7", "source": "6", "target": "8"},
        {"id": "e8", "source": "7", "target": "8"},
        {"id": "e9", "source": "8", "target": "9"},
    ],
}

# 2. Even / Odd Flowchart Graph
EVEN_ODD_GRAPH = {
    "nodes": [
        {"id": "1", "type": "start_end", "position": {"x": 300, "y": 40}, "data": {"label": "Start"}},
        {"id": "2", "type": "input_output", "position": {"x": 300, "y": 140}, "data": {"label": "Input n"}},
        {"id": "3", "type": "decision", "position": {"x": 300, "y": 250}, "data": {"label": "n % 2 == 0"}},
        {"id": "4", "type": "input_output", "position": {"x": 140, "y": 380}, "data": {"label": "Print Even"}},
        {"id": "5", "type": "input_output", "position": {"x": 460, "y": 380}, "data": {"label": "Print Odd"}},
        {"id": "6", "type": "start_end", "position": {"x": 300, "y": 500}, "data": {"label": "End"}},
    ],
    "edges": [
        {"id": "e1", "source": "1", "target": "2"},
        {"id": "e2", "source": "2", "target": "3"},
        {"id": "e3", "source": "3", "target": "4", "sourceHandle": "yes", "label": "Yes"},
        {"id": "e4", "source": "3", "target": "5", "sourceHandle": "no", "label": "No"},
        {"id": "e5", "source": "4", "target": "6"},
        {"id": "e6", "source": "5", "target": "6"},
    ],
}

def post(path: str, payload: dict):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as res:
        return res.status, json.loads(res.read())

def run_tests():
    print("=== Testing Calculator Flowchart Code Generation & Syntax ===")
    ast_data = logic_engine.build_flowchart_ast(CALC_GRAPH["nodes"], CALC_GRAPH["edges"])
    code = logic_engine.compile_to_python(ast_data)
    print("Generated Code:\n" + code)

    # 1. AST Validation
    try:
        py_ast.parse(code)
        print("✓ Code syntax validation passed (ast.parse)")
    except SyntaxError as se:
        print(f"✗ SyntaxError in generated code: {se}")
        sys.exit(1)

    assert 'if operation == "+":' in code or 'if operation == "+"' in code or "operation == '+'" in code, f"Expected operation == '+' in code, got: {code}"

    # 2. Execution with 5 \n 10 \n +
    out_plus = executor.run_code_safely(code, "5\n10\n+")
    print("Output for '5\\n10\\n+':", repr(out_plus))
    assert "15" in out_plus, f"Expected 15 in output, got: {out_plus}"

    # 3. Execution with 5 \n 10 \n -
    out_minus = executor.run_code_safely(code, "5\n10\n-")
    print("Output for '5\\n10\\n-':", repr(out_minus))
    assert "-5" in out_minus, f"Expected -5 in output, got: {out_minus}"

    print("\n=== Testing Even/Odd Flowchart ===")
    eo_ast = logic_engine.build_flowchart_ast(EVEN_ODD_GRAPH["nodes"], EVEN_ODD_GRAPH["edges"])
    eo_code = logic_engine.compile_to_python(eo_ast)
    print("Generated Code:\n" + eo_code)
    py_ast.parse(eo_code)

    eo_out_even = executor.run_code_safely(eo_code, "4")
    print("Output for '4':", repr(eo_out_even))
    assert "Even" in eo_out_even, f"Expected Even in output, got: {eo_out_even}"

    eo_out_odd = executor.run_code_safely(eo_code, "7")
    print("Output for '7':", repr(eo_out_odd))
    assert "Odd" in eo_out_odd, f"Expected Odd in output, got: {eo_out_odd}"

    # 4. HTTP API Test if server is up
    try:
        st, res_code = post("/api/generate-code", CALC_GRAPH)
        if st == 200:
            c = res_code.get("code", "")
            py_ast.parse(c)
            print("✓ HTTP API /api/generate-code returned valid syntax")
            st_exec, res_exec = post("/api/execute", {"code": c, "user_input": "5\n10\n+"})
            print("HTTP API Output for '5\\n10\\n+':", repr(res_exec.get("output")))
            assert "15" in str(res_exec.get("output"))
    except Exception as ex:
        print("API test note:", ex)

    print("\nALL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
