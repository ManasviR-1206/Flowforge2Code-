"""
Regression tests reproducing the screenshot bug and verifying flowchart compilation/execution.

Covers:
1. Exact reproduction of the screenshot's failure:
   Incomplete flowchart (Input n, fact = 1, i < n?, fact = fact, Print fact)
   must be cleanly rejected with HTTP 422 citing uninitialized variable 'i'.
2. Complete factorial flowchart compilation and execution with input 5 -> output 120.
3. Valid Even/Odd flowchart compilation and execution with inputs 4 -> Even, 7 -> Odd.
4. /api/generate-flowchart with "Calculate factorial" produces the complete, executable 9-node graph.
5. ARIA chat code generation trigger properly validates graph completeness.
"""

import ast as py_ast
import os
import pytest
from starlette.testclient import TestClient

import api_server
import logic_engine
import executor


client = TestClient(api_server.app)


def test_screenshot_failure_reproduced_and_rejected():
    """
    Reproduces the exact failure from the user's workspace screenshot:
    Nodes: Start, Input n, fact = 1, i < n?, fact = fact, Print fact, End.
    Loops fact = fact back to i < n? without defining or incrementing i.
    
    Must NOT generate code that raises NameError at runtime.
    Must return HTTP 422 explaining that variable 'i' is uninitialized.
    """
    screenshot_nodes = [
        {"id": "1", "type": "start_end", "position": {"x": 300, "y": 40}, "data": {"label": "Start"}},
        {"id": "2", "type": "input_output", "position": {"x": 300, "y": 140}, "data": {"label": "Input n"}},
        {"id": "3", "type": "process", "position": {"x": 300, "y": 240}, "data": {"label": "fact = 1"}},
        {"id": "4", "type": "decision", "position": {"x": 300, "y": 340}, "data": {"label": "i < n?"}},
        {"id": "5", "type": "process", "position": {"x": 140, "y": 460}, "data": {"label": "fact = fact"}},
        {"id": "6", "type": "input_output", "position": {"x": 460, "y": 460}, "data": {"label": "Print fact"}},
        {"id": "7", "type": "start_end", "position": {"x": 300, "y": 580}, "data": {"label": "End"}},
    ]
    screenshot_edges = [
        {"id": "e1", "source": "1", "target": "2"},
        {"id": "e2", "source": "2", "target": "3"},
        {"id": "e3", "source": "3", "target": "4"},
        {"id": "e4", "source": "4", "target": "5", "sourceHandle": "yes", "label": "Yes"},
        {"id": "e5", "source": "4", "target": "6", "sourceHandle": "no", "label": "No"},
        {"id": "e6", "source": "5", "target": "4"},  # loop-back edge to decision
        {"id": "e7", "source": "6", "target": "7"},
    ]

    # 1. Compiler directly rejects with ValueError citing 'i'
    ast_data = logic_engine.build_flowchart_ast(screenshot_nodes, screenshot_edges)
    with pytest.raises(ValueError) as excinfo:
        logic_engine.compile_to_python(ast_data)
    assert "'i'" in str(excinfo.value)
    assert "never defined or initialized" in str(excinfo.value)

    # 2. /api/generate-code endpoint returns HTTP 422
    resp = client.post("/api/generate-code", json={"nodes": screenshot_nodes, "edges": screenshot_edges})
    assert resp.status_code == 422
    detail = resp.json().get("detail", "")
    assert "'i'" in detail
    assert "initialization" in detail.lower()
    # Confirm misleading warning string is NOT present
    assert "The deterministic compiler output is recommended instead" not in detail


def test_valid_factorial_flowchart_compiles_and_runs_5_to_120():
    """
    Complete, valid factorial flowchart with initialization, condition, multiplication,
    increment, and loop-back compiles cleanly and produces 120 for input 5.
    """
    factorial_nodes = [
        {"id": "1", "type": "start_end", "position": {"x": 300, "y": 30}, "data": {"label": "Start"}},
        {"id": "2", "type": "input_output", "position": {"x": 300, "y": 120}, "data": {"label": "Input n"}},
        {"id": "3", "type": "process", "position": {"x": 300, "y": 210}, "data": {"label": "fact = 1"}},
        {"id": "4", "type": "process", "position": {"x": 300, "y": 300}, "data": {"label": "i = 1"}},
        {"id": "5", "type": "decision", "position": {"x": 300, "y": 400}, "data": {"label": "i <= n?"}},
        {"id": "6", "type": "process", "position": {"x": 140, "y": 530}, "data": {"label": "fact = fact * i"}},
        {"id": "7", "type": "process", "position": {"x": 140, "y": 620}, "data": {"label": "i = i + 1"}},
        {"id": "8", "type": "input_output", "position": {"x": 460, "y": 530}, "data": {"label": "Print fact"}},
        {"id": "9", "type": "start_end", "position": {"x": 300, "y": 720}, "data": {"label": "End"}},
    ]
    factorial_edges = [
        {"id": "e1", "source": "1", "target": "2"},
        {"id": "e2", "source": "2", "target": "3"},
        {"id": "e3", "source": "3", "target": "4"},
        {"id": "e4", "source": "4", "target": "5"},
        {"id": "e5", "source": "5", "target": "6", "sourceHandle": "yes", "label": "Yes"},
        {"id": "e6", "source": "6", "target": "7"},
        {"id": "e7", "source": "7", "target": "5"},  # loop-back to decision
        {"id": "e8", "source": "5", "target": "8", "sourceHandle": "no", "label": "No"},
        {"id": "e9", "source": "8", "target": "9"},
    ]

    # Generate code via API
    resp = client.post("/api/generate-code", json={"nodes": factorial_nodes, "edges": factorial_edges})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    code = data["code"]
    assert data["source"] == "compiler"

    # Verify syntax and structure
    parsed = py_ast.parse(code)
    assert parsed is not None
    assert "fact = 1" in code
    assert "i = 1" in code
    assert "while i <= n:" in code or "while" in code
    assert "fact = fact * i" in code
    assert "i = i + 1" in code
    assert "print(fact)" in code

    # Execute with input 5
    old_env = os.environ.get("FLOWFORGE_EXECUTION")
    try:
        os.environ["FLOWFORGE_EXECUTION"] = "local-dev"
        exec_resp = client.post("/api/execute", json={"code": code, "user_input": "5\n"})
        assert exec_resp.status_code == 200, exec_resp.text
        exec_data = exec_resp.json()
        assert exec_data["success"] is True
        output = exec_data["output"]
        assert "120" in output, f"Expected 120 in output, got:\n{output}"
    finally:
        if old_env is not None:
            os.environ["FLOWFORGE_EXECUTION"] = old_env
        else:
            os.environ.pop("FLOWFORGE_EXECUTION", None)


def test_valid_even_odd_flowchart_compiles_and_runs():
    """
    Valid Even/Odd flowchart compiles and correctly outputs 'Even' for 4 and 'Odd' for 7.
    """
    even_odd_nodes = [
        {"id": "1", "type": "start_end", "position": {"x": 300, "y": 40}, "data": {"label": "Start"}},
        {"id": "2", "type": "input_output", "position": {"x": 300, "y": 140}, "data": {"label": "Input n"}},
        {"id": "3", "type": "decision", "position": {"x": 300, "y": 250}, "data": {"label": "n % 2 == 0?"}},
        {"id": "4", "type": "input_output", "position": {"x": 140, "y": 390}, "data": {"label": 'Print "Even"'}},
        {"id": "5", "type": "input_output", "position": {"x": 460, "y": 390}, "data": {"label": 'Print "Odd"'}},
        {"id": "6", "type": "start_end", "position": {"x": 300, "y": 520}, "data": {"label": "End"}},
    ]
    even_odd_edges = [
        {"id": "e1", "source": "1", "target": "2"},
        {"id": "e2", "source": "2", "target": "3"},
        {"id": "e3", "source": "3", "target": "4", "sourceHandle": "yes", "label": "Yes"},
        {"id": "e4", "source": "3", "target": "5", "sourceHandle": "no", "label": "No"},
        {"id": "e5", "source": "4", "target": "6"},
        {"id": "e6", "source": "5", "target": "6"},
    ]

    resp = client.post("/api/generate-code", json={"nodes": even_odd_nodes, "edges": even_odd_edges})
    assert resp.status_code == 200, resp.text
    code = resp.json()["code"]

    old_env = os.environ.get("FLOWFORGE_EXECUTION")
    try:
        os.environ["FLOWFORGE_EXECUTION"] = "local-dev"
        # Test 4 -> Even
        exec_4 = client.post("/api/execute", json={"code": code, "user_input": "4\n"}).json()
        assert exec_4["success"] is True
        assert "Even" in exec_4["output"]

        # Test 7 -> Odd
        exec_7 = client.post("/api/execute", json={"code": code, "user_input": "7\n"}).json()
        assert exec_7["success"] is True
        assert "Odd" in exec_7["output"]
    finally:
        if old_env is not None:
            os.environ["FLOWFORGE_EXECUTION"] = old_env
        else:
            os.environ.pop("FLOWFORGE_EXECUTION", None)


def test_generate_flowchart_factorial_prompt_returns_complete_graph():
    """
    /api/generate-flowchart for 'Calculate factorial' returns a valid, complete 9-node graph
    with loop initialization and loop increment, avoiding LLM hallucinations.
    """
    resp = client.post("/api/generate-flowchart", json={"prompt": "Calculate factorial"})
    assert resp.status_code == 200, resp.text
    graph = resp.json()
    nodes = graph["nodes"]
    edges = graph["edges"]

    labels = [n.get("data", {}).get("label", "") for n in nodes]
    assert any("fact = 1" in l for l in labels), f"Missing fact = 1 in labels: {labels}"
    assert any("i = 1" in l for l in labels), f"Missing i = 1 in labels: {labels}"
    assert any("i <= n" in l or "i < n" in l for l in labels), f"Missing decision in labels: {labels}"
    assert any("fact * i" in l or "fact*i" in l for l in labels), f"Missing multiplication in labels: {labels}"
    assert any("i + 1" in l or "i+1" in l for l in labels), f"Missing increment in labels: {labels}"

    # Compile the generated graph
    code_resp = client.post("/api/generate-code", json={"nodes": nodes, "edges": edges})
    assert code_resp.status_code == 200, code_resp.text
    code = code_resp.json()["code"]

    old_env = os.environ.get("FLOWFORGE_EXECUTION")
    try:
        os.environ["FLOWFORGE_EXECUTION"] = "local-dev"
        exec_resp = client.post("/api/execute", json={"code": code, "user_input": "5\n"}).json()
        assert exec_resp["success"] is True
        assert "120" in exec_resp["output"]
    finally:
        if old_env is not None:
            os.environ["FLOWFORGE_EXECUTION"] = old_env
        else:
            os.environ.pop("FLOWFORGE_EXECUTION", None)


def test_aria_chat_generate_code_rejects_incomplete_graph():
    """
    ARIA chat trigger for 'generate_code' does not emit broken Python for an incomplete graph.
    """
    incomplete_nodes = [
        {"id": "1", "type": "start_end", "data": {"label": "Start"}},
        {"id": "2", "type": "decision", "data": {"label": "x > 0?"}},
        {"id": "3", "type": "input_output", "data": {"label": 'Print "OK"'}},
        {"id": "4", "type": "start_end", "data": {"label": "End"}},
    ]
    incomplete_edges = [
        {"id": "e1", "source": "1", "target": "2"},
        {"id": "e2", "source": "2", "target": "3", "label": "Yes", "sourceHandle": "yes"},
        {"id": "e3", "source": "2", "target": "4", "label": "No", "sourceHandle": "no"},
        {"id": "e4", "source": "3", "target": "4"},
    ]

    resp = client.post("/api/chat", json={
        "message": "generate code",
        "nodes": incomplete_nodes,
        "edges": incomplete_edges,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("error") is True or "incomplete" in data.get("reply", "").lower()
    assert "'x'" in data.get("reply", "") or "x" in data.get("reply", "")
