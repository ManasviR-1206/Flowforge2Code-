"""
FlowForge AI – Unified FastAPI Backend
Serves the React/Vite SPA and provides all REST API endpoints.
"""

import ast as py_ast
import base64
import io
import json
import os
import re
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image

import cv_engine
import ocr_engine
import logic_engine
import llm_generator
import executor

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

app = FastAPI(title="FlowForge AI API", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AI_UNAVAILABLE = "AI generation is currently unavailable. Please configure the backend API key."


def pil_from_upload(file_bytes: bytes) -> Image.Image:
    return Image.open(io.BytesIO(file_bytes)).convert("RGB")


def img_to_b64(cv_img: np.ndarray) -> str:
    _, buf = cv2.imencode(".png", cv_img)
    return base64.b64encode(buf).decode("utf-8")


def get_gemini_model(model_name: str = "gemini-3.8-flash"):
    if not GEMINI_API_KEY:
        raise HTTPException(503, AI_UNAVAILABLE)
    try:
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        last_err = None
        for name in (model_name, "gemini-3.8-flash"):
            try:
                return genai.GenerativeModel(name)
            except Exception as e:
                last_err = e
        raise last_err or RuntimeError("No Gemini model available")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(503, f"AI generation is currently unavailable: {str(e)}")


def generate_sample_flowchart_cv() -> np.ndarray:
    canvas = np.ones((620, 700, 3), dtype=np.uint8) * 255
    cv2.ellipse(canvas, (350, 45), (72, 26), 0, 0, 360, (0, 0, 0), 2)
    cv2.putText(canvas, "Start", (325, 51), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

    input_pts = np.array([[290, 105], [430, 105], [408, 160], [268, 160]], np.int32)
    cv2.polylines(canvas, [input_pts], True, (0, 0, 0), 2)
    cv2.putText(canvas, "Input n", (320, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)
    cv2.arrowedLine(canvas, (350, 72), (350, 102), (0, 0, 0), 2, tipLength=0.25)

    decision_pts = np.array([[350, 200], [430, 255], [350, 310], [270, 255]], np.int32)
    cv2.polylines(canvas, [decision_pts], True, (0, 0, 0), 2)
    cv2.putText(canvas, "n % 2 == 0?", (300, 261), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 2)
    cv2.arrowedLine(canvas, (350, 160), (350, 198), (0, 0, 0), 2, tipLength=0.25)

    left_pts = np.array([[75, 365], [250, 365], [230, 415], [55, 415]], np.int32)
    right_pts = np.array([[450, 365], [625, 365], [605, 415], [430, 415]], np.int32)
    cv2.polylines(canvas, [left_pts, right_pts], True, (0, 0, 0), 2)
    cv2.putText(canvas, 'Print "Even"', (95, 398), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
    cv2.putText(canvas, 'Print "Odd"', (475, 398), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
    cv2.putText(canvas, "Yes", (230, 330), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
    cv2.putText(canvas, "No", (455, 330), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
    cv2.arrowedLine(canvas, (270, 255), (155, 362), (0, 0, 0), 2, tipLength=0.15)
    cv2.arrowedLine(canvas, (430, 255), (535, 362), (0, 0, 0), 2, tipLength=0.15)

    cv2.ellipse(canvas, (350, 555), (72, 26), 0, 0, 360, (0, 0, 0), 2)
    cv2.putText(canvas, "End", (335, 561), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    cv2.arrowedLine(canvas, (155, 415), (350, 526), (0, 0, 0), 2, tipLength=0.15)
    cv2.arrowedLine(canvas, (535, 415), (350, 526), (0, 0, 0), 2, tipLength=0.15)
    return canvas


NODE_TYPE_MAP = {
    "start_end": "start_end",
    "input_output": "input_output",
    "decision": "decision",
    "process": "process",
    "unknown": "process",
    "manual_input": "manual_input",
    "database": "database",
    "document": "document",
    "connector": "connector",
    "offpage": "offpage",
    "predefined_process": "predefined_process",
    "delay": "delay",
}


def blocks_to_react_nodes(blocks, img_height=500, img_width=400) -> list:
    nodes = []
    placeholder_labels = {
        "start_end": "Start / End",
        "input_output": "Unlabeled input/output",
        "decision": "Unlabeled decision",
        "process": "Unlabeled process",
        "manual_input": "Unlabeled input",
    }
    for i, b in enumerate(blocks):
        shape_type = b.get("type", "process")
        text = b.get("text", "").strip()
        bbox = b.get("bbox", (0, 0, 50, 50))
        cx = b.get("center", (img_width // 2, (i + 1) * 100))[0]
        cy = b.get("center", (img_width // 2, (i + 1) * 100))[1]
        if not text:
            if shape_type == "start_end":
                text = "Start" if cy <= img_height / 2 else "End"
            else:
                text = placeholder_labels.get(shape_type, "Unlabeled flowchart step")
        x = int((cx / max(img_width, 1)) * 550) + 50
        y = int((cy / max(img_height, 1)) * 600) + 30
        nodes.append({
            "id": str(b["id"]),
            "type": NODE_TYPE_MAP.get(shape_type, "process"),
            "position": {"x": x, "y": y},
            "data": {"label": text},
        })
    return nodes


def connections_to_react_edges(connections) -> list:
    edges = []
    for i, c in enumerate(connections):
        label = c.get("branch") or ""
        handle = "yes" if str(label).lower() in ("yes", "true") else ("no" if str(label).lower() in ("no", "false") else None)
        e = {
            "id": f"e_{i}",
            "source": str(c["from"]),
            "target": str(c["to"]),
            "type": "smoothstep",
            "animated": True,
            "label": label,
        }
        if handle:
            e["sourceHandle"] = handle
        edges.append(e)
    return edges


def parse_json_object(raw: str) -> dict:
    raw = (raw or "").strip()
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        raise ValueError("No JSON found in response")
    return json.loads(match.group())


def parse_json_array(raw: str) -> list:
    match = re.search(r"\[.*\]", raw or "", re.DOTALL)
    if not match:
        return []
    return json.loads(match.group())


def normalize_ai_flowchart(data: dict) -> dict:
    nodes, edges = logic_engine.sanitize_graph(data.get("nodes") or [], data.get("edges") or [])
    if not nodes:
        raise ValueError("Generated flowchart has no nodes")
    return {"nodes": nodes, "edges": edges}


FLOWCHART_JSON_SCHEMA = """
Return ONLY a JSON object (no markdown, no explanation) in this exact schema:
{
  "nodes": [
    {"id": "1", "type": "start_end", "position": {"x": 300, "y": 50}, "data": {"label": "Start"}},
    {"id": "2", "type": "input_output", "position": {"x": 300, "y": 150}, "data": {"label": "Input n"}}
  ],
  "edges": [
    {"id": "e1-2", "source": "1", "target": "2", "type": "smoothstep", "animated": true, "label": ""},
    {"id": "e3-4", "source": "3", "target": "4", "sourceHandle": "yes", "type": "smoothstep", "animated": true, "label": "Yes"}
  ]
}

Allowed node types: start_end, process, input_output, decision, document, predefined_process, database, manual_input, connector, offpage, delay
- start_end: oval Start/End
- process: rectangle
- input_output: parallelogram (input / print)
- decision: diamond; MUST have Yes and No outgoing edges labeled "Yes"/"No" with sourceHandle yes/no
Always include Start and End. Layout top-to-bottom around x=300. Merge branches into shared End when they reconverge.
"""


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "service": "FlowForge AI API",
        "ai_available": bool(GEMINI_API_KEY),
    }


@app.post("/api/analyze")
async def analyze(
    file: Optional[UploadFile] = File(None),
    mode: str = Form("upload"),
    canvas_data: Optional[str] = Form(None),
):
    try:
        if mode == "sample":
            cv_bgr = generate_sample_flowchart_cv()
            pil_img = Image.fromarray(cv2.cvtColor(cv_bgr, cv2.COLOR_BGR2RGB))
        elif mode == "canvas" and canvas_data:
            img_bytes = base64.b64decode(canvas_data.split(",")[-1])
            pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        elif file:
            contents = await file.read()
            if len(contents) < 100:
                raise HTTPException(400, "Uploaded file appears to be empty or too small.")
            name = (file.filename or "").lower()
            if name and not name.endswith((".png", ".jpg", ".jpeg")):
                raise HTTPException(400, "Invalid image file. Please upload a PNG, JPG, or JPEG.")
            try:
                pil_img = pil_from_upload(contents)
            except Exception:
                raise HTTPException(400, "Invalid image file. Please upload a PNG, JPG, or JPEG.")
        else:
            raise HTTPException(400, "No image provided. Please upload a PNG, JPG, or JPEG.")

        norm_img = cv_engine.normalize_image(pil_img)
        h, w = norm_img.shape[:2]
        blocks, thresh = cv_engine.detect_symbols(norm_img)

        if not blocks:
            raise HTTPException(422, "No flowchart symbols detected. Please ensure the image contains clear shapes.")

        connections = cv_engine.detect_connections(thresh, blocks)

        ocr_failed = 0
        for b in blocks:
            try:
                b["text"] = ocr_engine.extract_block_text(norm_img, b["bbox"])
                if not b["text"]:
                    ocr_failed += 1
            except Exception:
                b["text"] = ""
                ocr_failed += 1

        overlay = cv_engine.overlay_detections(norm_img, blocks, connections)
        overlay_b64 = img_to_b64(overlay)

        react_nodes = blocks_to_react_nodes(blocks, img_height=h, img_width=w)
        react_edges = connections_to_react_edges(connections)

        blocks_json = [
            {"id": b["id"], "type": b["type"], "text": b["text"],
             "bbox": list(b["bbox"]), "center": list(b["center"])}
            for b in blocks
        ]
        connections_json = [{"from": c["from"], "to": c["to"], "branch": c.get("branch", "")} for c in connections]

        warning = None
        if ocr_failed:
            warning = (
                f"Could not read text from {ocr_failed} of {len(blocks)} detected shapes. "
                "Please review and edit those node labels on the canvas."
            )

        return JSONResponse({
            "nodes": react_nodes,
            "edges": react_edges,
            "blocks": blocks_json,
            "connections": connections_json,
            "overlay_image": overlay_b64,
            "warning": warning,
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Analysis failed: {str(e)}")


@app.post("/api/generate-flowchart")
async def generate_flowchart(request_body: dict):
    prompt = (request_body.get("prompt") or "").strip()
    if not prompt:
        raise HTTPException(400, "Prompt is required. Describe the program you want to build.")

    local = logic_engine.prompt_to_flowchart(prompt)
    if local:
        if not GEMINI_API_KEY:
            return JSONResponse(local)
        # Prefer the built-in deterministic flowchart for common teaching patterns to keep
        # credit usage low and avoid quota failures when Gemini is rate-limited.
        try:
            model = get_gemini_model()
            system_prompt = f"""You are a flowchart designer. Given a programming task, create a detailed flowchart JSON.
The flowchart is the source of truth — do NOT emit Python code.

{FLOWCHART_JSON_SCHEMA}

User request: {prompt}"""
            response = model.generate_content(system_prompt)
            data = normalize_ai_flowchart(parse_json_object(response.text))
            return JSONResponse(data)
        except Exception:
            return JSONResponse(local)

    if not GEMINI_API_KEY:
        raise HTTPException(503, AI_UNAVAILABLE)

    try:
        model = get_gemini_model()
        system_prompt = f"""You are a flowchart designer. Given a programming task, create a detailed flowchart JSON.
The flowchart is the source of truth — do NOT emit Python code.

{FLOWCHART_JSON_SCHEMA}

User request: {prompt}"""
        response = model.generate_content(system_prompt)
        data = normalize_ai_flowchart(parse_json_object(response.text))
        return JSONResponse(data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(503, f"AI generation is currently unavailable or quota-limited: {str(e)}")


@app.post("/api/generate-code")
async def generate_code(request_body: dict):
    try:
        nodes = request_body.get("nodes", [])
        edges = request_body.get("edges", [])
        if not nodes:
            raise HTTPException(400, "Canvas is empty. Please create a flowchart first.")

        nodes, edges = logic_engine.sanitize_graph(nodes, edges)
        unlabeled = [
            logic_engine.node_text(node)
            for node in nodes
            if not logic_engine.node_text(node)
            or logic_engine.node_text(node).lower().startswith("unlabeled")
        ]
        if unlabeled:
            raise HTTPException(
                422,
                "Some imported flowchart labels could not be read. Edit the highlighted or unlabeled nodes, then generate Python again.",
            )
        ast_data = logic_engine.build_flowchart_ast(nodes, edges)
        code = llm_generator.generate_python_code(ast_data, GEMINI_API_KEY or None)

        warnings = []
        try:
            py_ast.parse(code)
        except SyntaxError:
            code = logic_engine.compile_to_python(ast_data)
            warnings.append("LLM code had syntax errors; using the flowchart compiler instead.")

        try:
            py_ast.parse(code)
        except SyntaxError as se:
            raise HTTPException(
                422,
                f"The current flowchart could not be translated to valid Python: {se.msg} (line {se.lineno}).",
            )

        warnings.extend(logic_engine.consistency_warnings(ast_data, code))
        return JSONResponse({"code": code, "ast": ast_data, "warnings": warnings})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Code generation failed: {str(e)}")


@app.post("/api/execute")
async def execute_code(request_body: dict):
    try:
        code = (request_body.get("code") or "").strip()
        user_input = request_body.get("user_input", "")
        if not code:
            raise HTTPException(400, "No code to execute. Generate Python from your flowchart first.")
        try:
            py_ast.parse(code)
        except SyntaxError as se:
            msg = f"Syntax Error: {str(se)}"
            return JSONResponse({"output": msg, "stdout": "", "stderr": msg, "status": "error", "success": False, "error_details": msg, "program_output": ""})
        output = executor.run_code_safely(code, user_input, timeout_sec=5)
        output_text = str(output or "")
        is_error = (
            output_text.startswith(("Execution Error", "Syntax Error", "Security Error"))
            or "Traceback (most recent call last):" in output_text
            or "EOFError" in output_text
            or "Exception" in output_text
            or "Error:" in output_text
        )
        status = "error" if is_error else "success"
        stdout = output_text
        error_details = ""
        program_output = output_text.strip()
        if status == "error":
            error_details = output_text.strip()
            program_output = ""
        else:
            cleaned_lines = []
            for line in output_text.splitlines():
                stripped = line.strip()
                if re.fullmatch(r"Enter\s+.*?:", stripped):
                    continue
                if re.fullmatch(r"Enter\s+.*?:\s*", stripped):
                    continue
                cleaned_lines.append(line)
            program_output = "\n".join(part for part in cleaned_lines if part.strip() or part == "").strip()
            if not program_output:
                program_output = output_text.strip()
        return JSONResponse({
            "output": output_text,
            "stdout": stdout,
            "stderr": error_details if status == "error" else "",
            "status": status,
            "success": status == "success",
            "error_details": error_details,
            "program_output": program_output,
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Execution failed: {str(e)}")


@app.post("/api/debug")
async def debug_flowchart(request_body: dict):
    nodes = request_body.get("nodes", [])
    edges = request_body.get("edges", [])
    issues = logic_engine.analyze_graph_structure(nodes, edges)

    if GEMINI_API_KEY:
        try:
            model = get_gemini_model()
            ast_data = logic_engine.build_flowchart_ast(nodes, edges)
            prompt = f"""Analyze this flowchart AST for logical errors (not style advice).
Flowchart: {json.dumps(ast_data, indent=2)}
Return ONLY a JSON array of {{"type":"warning","message":"...","node_id":"id_or_null"}}. If none, []."""
            response = model.generate_content(prompt)
            issues.extend(parse_json_array(response.text))
        except Exception:
            pass

    errors = [i for i in issues if i.get("type") == "error"]
    valid = len(issues) == 0
    summary = "✓ Flowchart valid" if valid else f"⚠ {len(issues)} issue{'s' if len(issues) != 1 else ''} found"
    return JSONResponse({"issues": issues, "valid": valid, "summary": summary, "error_count": len(errors)})


@app.post("/api/debug/fix")
async def fix_flowchart(request_body: dict):
    nodes = request_body.get("nodes", [])
    edges = request_body.get("edges", [])
    issues = request_body.get("issues", [])
    nodes, edges = logic_engine.auto_fix_graph(nodes, edges, issues)

    if GEMINI_API_KEY:
        try:
            model = get_gemini_model()
            prompt = f"""Fix these flowchart issues and return COMPLETE corrected JSON.
Current nodes: {json.dumps(nodes, indent=2)}
Current edges: {json.dumps(edges, indent=2)}
Issues: {json.dumps(issues, indent=2)}
{FLOWCHART_JSON_SCHEMA}"""
            response = model.generate_content(prompt)
            data = normalize_ai_flowchart(parse_json_object(response.text))
            return JSONResponse(data)
        except Exception:
            pass

    nodes, edges = logic_engine.sanitize_graph(nodes, edges)
    return JSONResponse({"nodes": nodes, "edges": edges})


@app.post("/api/chat")
async def aria_chat(request_body: dict):
    message = (request_body.get("message") or "").strip()
    nodes = request_body.get("nodes") or []
    edges = request_body.get("edges") or []
    if not message:
        raise HTTPException(400, "Message is required.")

    nodes, edges = logic_engine.sanitize_graph(nodes, edges)
    local = logic_engine.local_chat_handler(message, nodes, edges)
    low = message.lower()

    wants_new_flow = any(k in low for k in ("create a flowchart", "generate flowchart", "new flowchart", "build a flowchart"))
    if wants_new_flow:
        built = logic_engine.prompt_to_flowchart(message)
        if GEMINI_API_KEY:
            try:
                model = get_gemini_model()
                system_prompt = f"""You are ARIA. Create a flowchart JSON for the user request. Return JSON:
{{"reply":"short confirmation","patch":{{"action":"replace","nodes":[...],"edges":[...]}}}}
{FLOWCHART_JSON_SCHEMA}
User: {message}
Current graph: {json.dumps({"nodes": nodes, "edges": edges})}"""
                response = model.generate_content(system_prompt)
                data = parse_json_object(response.text)
                patch = data.get("patch")
                if patch and patch.get("nodes"):
                    nf = normalize_ai_flowchart(patch)
                    patch = {"action": "replace", **nf}
                return JSONResponse({"reply": data.get("reply") or "Created a new flowchart on the canvas.", "patch": patch})
            except Exception:
                if built:
                    return JSONResponse({"reply": "I created a flowchart on the canvas from your request.", "patch": {"action": "replace", **built}})
        elif built:
            return JSONResponse({"reply": "I created a flowchart on the canvas from your request.", "patch": {"action": "replace", **built}})
        elif not GEMINI_API_KEY:
            raise HTTPException(503, AI_UNAVAILABLE)

    if local and local.get("patch"):
        patch = local["patch"]
        if (patch.get("action") or "replace").lower() == "replace" and patch.get("nodes") is not None:
            nn, ee = logic_engine.sanitize_graph(patch.get("nodes") or [], patch.get("edges") or [])
            local["patch"] = {"action": "replace", "nodes": nn, "edges": ee}
        else:
            nn, ee = logic_engine.apply_patch(nodes, edges, patch)
            nn, ee = logic_engine.sanitize_graph(nn, ee)
            local["patch"] = {"action": "replace", "nodes": nn, "edges": ee}
        return JSONResponse(local)

    if local and local.get("trigger") == "generate_code":
        if not nodes:
            return JSONResponse({"reply": "The canvas is empty. Add a flowchart first, then I can generate Python.", "patch": None, "trigger": None})
        ast_data = logic_engine.build_flowchart_ast(nodes, edges)
        code = llm_generator.generate_python_code(ast_data, GEMINI_API_KEY or None)
        return JSONResponse({
            "reply": "Generated Python from the current flowchart. It is now in the code panel.",
            "patch": None,
            "trigger": "generate_code",
            "code": code,
            "warnings": logic_engine.consistency_warnings(ast_data, code),
        })

    if local and not GEMINI_API_KEY:
        return JSONResponse(local)

    if not GEMINI_API_KEY:
        if local:
            return JSONResponse(local)
        raise HTTPException(503, AI_UNAVAILABLE)

    model = get_gemini_model()
    flowchart_context = json.dumps({"nodes": nodes, "edges": edges, "node_count": len(nodes), "edge_count": len(edges)}, indent=2)
    system_prompt = f"""You are ARIA, the FlowForge AI assistant. Help users build, debug, and understand flowcharts. The flowchart graph is the source of truth.

Current flowchart:
{flowchart_context}

When modifying the canvas, return a patch with action "replace" and COMPLETE nodes and edges arrays (never partial graphs for replace).
For add-only edits you may use action "add_nodes" with new_nodes and new_edges.
For a single label change use action "update_node" with node_id and data.label.

RESPONSE JSON:
{{
  "reply": "plain-language answer",
  "patch": null or {{ "action": "replace"|"add_nodes"|"update_node", "nodes": [], "edges": [], "new_nodes": [], "new_edges": [], "node_id": "", "data": {{}} }}
}}

{FLOWCHART_JSON_SCHEMA}

User message: {message}"""
    try:
        response = model.generate_content(system_prompt)
        raw = response.text.strip()
        try:
            data = parse_json_object(raw)
            reply = data.get("reply") or raw
            patch = data.get("patch")
            if patch:
                action = (patch.get("action") or "replace").lower()
                if action == "replace" and patch.get("nodes"):
                    patch = {"action": "replace", **normalize_ai_flowchart(patch)}
                else:
                    nn, ee = logic_engine.apply_patch(nodes, edges, patch)
                    nn, ee = logic_engine.sanitize_graph(nn, ee)
                    patch = {"action": "replace", "nodes": nn, "edges": ee}
        except Exception:
            reply = raw
            patch = None
        if local and not patch:
            return JSONResponse(local)
        return JSONResponse({"reply": reply, "patch": patch})
    except HTTPException:
        raise
    except Exception as e:
        if local:
            return JSONResponse(local)
        raise HTTPException(500, f"Chat failed: {str(e)}")


DIST_DIR = Path(__file__).parent / "landing" / "dist"

if DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(DIST_DIR / "assets")), name="assets")

    @app.get("/")
    async def serve_root():
        return FileResponse(str(DIST_DIR / "index.html"))

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        file_path = DIST_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(str(file_path))
        return FileResponse(str(DIST_DIR / "index.html"))
