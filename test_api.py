"""End-to-end verification of the flowchart graph → Python pipeline."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

import cv2

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import api_server
import logic_engine

BASE = os.environ.get("FLOWFORGE_API", "http://127.0.0.1:8000")
PASS = 0
FAIL = 0


def report(name: str, ok: bool, detail: str = ""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print("PASS  " + name + ((" - " + detail) if detail else ""))
    else:
        FAIL += 1
        print("FAIL  " + name + ((" - " + detail) if detail else ""))


def post(path: str, payload: dict | None = None, files: dict | None = None):
    if files:
        import uuid
        boundary = uuid.uuid4().hex
        body = b""
        for k, v in (payload or {}).items():
            body += f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode()
        for k, (filename, data, ctype) in files.items():
            body += (
                f"--{boundary}\r\nContent-Disposition: form-data; name=\"{k}\"; filename=\"{filename}\"\r\n"
                f"Content-Type: {ctype}\r\n\r\n"
            ).encode() + data + b"\r\n"
        body += f"--{boundary}--\r\n".encode()
        req = urllib.request.Request(
            BASE + path,
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
            method="POST",
        )
    else:
        req = urllib.request.Request(
            BASE + path,
            data=json.dumps(payload or {}).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
    try:
        with urllib.request.urlopen(req, timeout=180) as res:
            return res.status, json.loads(res.read())
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            data = json.loads(raw)
        except Exception:
            data = {"detail": raw.decode("utf-8", "replace")}
        return e.code, data


POSNEG = {
    "nodes": [
        {"id": "1", "type": "start_end", "position": {"x": 300, "y": 40}, "data": {"label": "Start"}},
        {"id": "2", "type": "input_output", "position": {"x": 300, "y": 140}, "data": {"label": "Input n"}},
        {"id": "3", "type": "decision", "position": {"x": 300, "y": 250}, "data": {"label": "n > 0?"}},
        {"id": "4", "type": "input_output", "position": {"x": 140, "y": 390}, "data": {"label": "Print Positive"}},
        {"id": "5", "type": "input_output", "position": {"x": 460, "y": 390}, "data": {"label": "Print Negative"}},
        {"id": "6", "type": "start_end", "position": {"x": 300, "y": 520}, "data": {"label": "End"}},
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


def test_local_compiler():
    ast = logic_engine.build_flowchart_ast(POSNEG["nodes"], POSNEG["edges"])
    code = logic_engine.compile_to_python(ast)
    report("A local compile has input/if/print", "input(" in code and "if " in code and "print(" in code, code.strip().replace("\n", " | "))
    out_pos = __import__("executor").run_code_safely(code, "5")
    out_neg = __import__("executor").run_code_safely(code, "-2")
    report("A run 5 -> Positive", "Positive" in out_pos, repr(out_pos.strip()))
    report("A run -2 -> Negative", "Negative" in out_neg, repr(out_neg.strip()))

    # Edit process node a+b → a*b
    nodes = [
        {"id": "1", "type": "start_end", "position": {"x": 0, "y": 0}, "data": {"label": "Start"}},
        {"id": "2", "type": "input_output", "position": {"x": 0, "y": 80}, "data": {"label": "Input a"}},
        {"id": "3", "type": "input_output", "position": {"x": 0, "y": 160}, "data": {"label": "Input b"}},
        {"id": "4", "type": "process", "position": {"x": 0, "y": 240}, "data": {"label": "sum = a + b"}},
        {"id": "5", "type": "input_output", "position": {"x": 0, "y": 320}, "data": {"label": "Print sum"}},
        {"id": "6", "type": "start_end", "position": {"x": 0, "y": 400}, "data": {"label": "End"}},
    ]
    edges = [
        {"id": "e1", "source": "1", "target": "2"},
        {"id": "e2", "source": "2", "target": "3"},
        {"id": "e3", "source": "3", "target": "4"},
        {"id": "e4", "source": "4", "target": "5"},
        {"id": "e5", "source": "5", "target": "6"},
    ]
    c1 = logic_engine.compile_to_python(logic_engine.build_flowchart_ast(nodes, edges))
    nodes[3]["data"]["label"] = "sum = a * b"
    c2 = logic_engine.compile_to_python(logic_engine.build_flowchart_ast(nodes, edges))
    report("F graph edit + to * changes code", "+" in c1 and "*" in c2 and "+" not in c2.split("sum")[-1], f"{c1.strip()} vs {c2.strip()}")

    chat = logic_engine.local_chat_handler("Add an input node for age", POSNEG["nodes"], POSNEG["edges"])
    added = any("age" in logic_engine.node_text(n).lower() for n in (chat or {}).get("patch", {}).get("nodes") or [])
    report("C local chat adds age input", bool(chat and chat.get("patch") and added), str((chat or {}).get("reply")))

    debug_nodes = [
        {"id": "1", "type": "start_end", "position": {"x": 0, "y": 0}, "data": {"label": "Start"}},
        {"id": "3", "type": "decision", "position": {"x": 0, "y": 80}, "data": {"label": "n > 0?"}},
        {"id": "4", "type": "input_output", "position": {"x": 0, "y": 160}, "data": {"label": "Print Positive"}},
    ]
    debug_edges = [
        {"id": "e1", "source": "1", "target": "3"},
        {"id": "e3", "source": "3", "target": "4", "label": "Yes", "sourceHandle": "yes"},
    ]
    issues = logic_engine.analyze_graph_structure(debug_nodes, debug_edges)
    msgs = " ".join(i["message"] for i in issues).lower()
    report("E missing NO branch", "missing" in msgs and "no" in msgs, msgs)
    report("E highlights decision", any(i.get("node_id") == "3" for i in issues))

    flow = logic_engine.prompt_to_flowchart("Create a program that checks whether a number is even or odd")
    report("B prompt builds flowchart first", bool(flow and flow.get("nodes") and flow.get("edges")))
    even_code = logic_engine.compile_to_python(logic_engine.build_flowchart_ast(flow["nodes"], flow["edges"]))
    report("B code from that flowchart", "input(" in even_code and ("% 2" in even_code or "even" in even_code.lower()), even_code.strip().replace("\n", " | "))


def test_api():
    try:
        with urllib.request.urlopen(BASE + "/api/health", timeout=5) as res:
            health = json.loads(res.read())
        report("health", health.get("status") == "ok")
    except Exception as e:
        report("health / API running", False, str(e))
        print("Start the backend: uvicorn api_server:app --port 8000")
        return

    st, data = post("/api/generate-code", POSNEG)
    code = (data.get("code") or "") if st == 200 else ""
    report("A generate-code", st == 200 and "input(" in code, code.strip().replace("\n", " | ")[:240])

    st, data = post("/api/execute", {"code": code, "user_input": "5"})
    report("A/G execute 5", st == 200 and "Positive" in str(data.get("output")), repr(data.get("output")))
    st, data = post("/api/execute", {"code": code, "user_input": "-2"})
    report("A execute -2", st == 200 and "Negative" in str(data.get("output")), repr(data.get("output")))

    st, data = post("/api/generate-flowchart", {"prompt": "Create a program that checks whether a number is even or odd"})
    ok = st == 200 and data.get("nodes")
    report("B generate-flowchart JSON", bool(ok), f"status={st} nodes={len(data.get('nodes') or [])}")
    if ok:
        st2, coded = post("/api/generate-code", {"nodes": data["nodes"], "edges": data.get("edges") or []})
        report("B code from AI/rule flowchart", st2 == 200 and "input(" in (coded.get("code") or ""), (coded.get("code") or "")[:200])

    st, data = post("/api/chat", {"message": "Add an input node for age", **POSNEG})
    patch = data.get("patch") or {}
    labels = [logic_engine.node_text(n).lower() for n in patch.get("nodes") or []]
    report("C chat patch age", st == 200 and any("age" in t for t in labels), data.get("reply"))

    png = api_server.generate_sample_flowchart_cv()
    ok_enc, buf = cv2.imencode(".png", png)
    report("D sample PNG created", bool(ok_enc))
    st, data = post("/api/analyze", {"mode": "upload"}, files={"file": ("sample.png", buf.tobytes(), "image/png")})
    imported_nodes = data.get("nodes") or []
    imported_edges = data.get("edges") or []
    imported_types = {node.get("type") for node in imported_nodes}
    detected_graph = (
        st == 200
        and len(imported_nodes) >= 6
        and {"start_end", "decision", "input_output"}.issubset(imported_types)
        and {
            (str(edge.get("source")), str(edge.get("target")))
            for edge in imported_edges
        } == {
            ("1", "2"),
            ("2", "3"),
            ("3", "4"),
            ("3", "5"),
            ("4", "6"),
            ("5", "6"),
        }
    )
    branch_labels = {str(edge.get("label", "")).lower() for edge in imported_edges}
    report(
        "D image upload detects symbols and directed graph topology",
        detected_graph,
        f"status={st} nodes={len(imported_nodes)} types={sorted(imported_types)} edges={len(imported_edges)} branches={sorted(branch_labels)}",
    )
    if st == 200 and data.get("nodes"):
        stc, coded = post("/api/generate-code", {"nodes": data["nodes"], "edges": data.get("edges") or []})
        if stc == 200:
            try:
                import ast
                ast.parse(coded.get("code") or "")
                generated_ok = bool(coded.get("code"))
            except SyntaxError:
                generated_ok = False
        else:
            generated_ok = stc == 422 and any(
                word in str(coded.get("detail", "")).lower()
                for word in ("label", "uncertain", "review")
            )
        report(
            "D uploaded graph generates valid code or reports uncertainty",
            generated_ok,
            (coded.get("code") or coded.get("detail") or "")[:180],
        )
        if stc == 200:
            for value, expected in (("10", "Even"), ("7", "Odd")):
                ste, execution = post("/api/execute", {"code": coded["code"], "user_input": value})
                report(
                    f"D uploaded graph run {value} -> {expected}",
                    ste == 200 and expected in str(execution.get("program_output") or execution.get("output")),
                    str(execution.get("program_output") or execution.get("output")),
                )

    bad_status, bad_image = post(
        "/api/analyze",
        {"mode": "upload"},
        files={"file": ("invalid.png", b"not-an-image" * 16, "image/png")},
    )
    report(
        "E invalid image returns a useful error",
        bad_status == 400 and "image" in str(bad_image.get("detail", "")).lower(),
        f"status={bad_status} {bad_image.get('detail') or ''}",
    )

    st, data = post("/api/debug", {
        "nodes": [
            {"id": "1", "type": "start_end", "position": {"x": 0, "y": 0}, "data": {"label": "Start"}},
            {"id": "3", "type": "decision", "position": {"x": 0, "y": 80}, "data": {"label": "n > 0?"}},
            {"id": "4", "type": "input_output", "position": {"x": 0, "y": 160}, "data": {"label": "Print Positive"}},
        ],
        "edges": [
            {"id": "e1", "source": "1", "target": "3"},
            {"id": "e3", "source": "3", "target": "4", "label": "Yes", "sourceHandle": "yes"},
        ],
    })
    msgs = " ".join(i.get("message", "") for i in data.get("issues") or []).lower()
    report("E debug missing NO", st == 200 and "missing" in msgs and "no" in msgs, data.get("summary"))
    report("E debug node_id", any(str(i.get("node_id")) == "3" for i in data.get("issues") or []))


if __name__ == "__main__":
    print("=== Local graph compiler ===")
    test_local_compiler()
    print("\n=== HTTP API ===")
    test_api()
    print(f"\n{PASS} passed, {FAIL} failed")
    sys.exit(1 if FAIL else 0)
