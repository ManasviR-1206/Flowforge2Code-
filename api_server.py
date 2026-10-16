"""
FlowForge AI – Unified FastAPI Backend
Serves the React/Vite SPA and provides all REST API endpoints.
"""

import asyncio
import ast as py_ast
import base64
import io
import json
import logging
import os
import re
import urllib.parse
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image, ImageOps

BASE_DIR = Path(__file__).resolve().parent
logger = logging.getLogger(__name__)
load_dotenv(BASE_DIR / ".env")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
MAX_IMAGE_UPLOAD_SIZE = 15 * 1024 * 1024  # 15 MB limit
ALLOWED_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".bmp")
OCR_REVIEW_CONFIDENCE = 50

import cv_engine
import ocr_engine
import logic_engine
import llm_generator
import executor

@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Verify the execution sandbox in the background so the first Run click is not slow.
    executor.warm_up()
    yield


app = FastAPI(title="FlowForge AI API", version="3.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_CONCURRENT_EXECUTIONS = int(os.getenv("FLOWFORGE_MAX_CONCURRENT_EXECUTIONS", "4"))
_execution_semaphore = asyncio.Semaphore(MAX_CONCURRENT_EXECUTIONS)
_active_executions = 0
_executions_lock = asyncio.Lock()


LOCAL_CLIENT_HOSTS = {"127.0.0.1", "::1", "localhost", "testclient"}
PROXY_HEADERS = ("x-forwarded-for", "x-forwarded-host", "x-real-ip", "forwarded", "via")


def _request_is_local(request: Request) -> bool:
    """True only for a direct connection from this machine (no reverse-proxy headers).

    Best-effort guard used ONLY for the unsafe `local-dev` execution mode, so that it
    cannot serve strangers by accident. It is not a substitute for not deploying that mode.
    """
    client = request.client.host if request.client else ""
    if client not in LOCAL_CLIENT_HOSTS:
        return False
    return not any(header in request.headers for header in PROXY_HEADERS)


@app.get("/api/health")
async def health_check():
    """Health check endpoint reporting AI availability and execution engine status."""
    exec_status = executor.execution_status(block=False)
    limits = executor.get_limits()
    return JSONResponse({
        "status": "ok",
        "ai_available": bool(GEMINI_API_KEY),
        "execution": exec_status,
        "backend": "FlowForge AI API",
        "version": "3.0.0",
    })

AI_UNAVAILABLE = "AI generation is currently unavailable. Please configure the backend API key."


def pil_from_upload(file_bytes: bytes) -> Image.Image:
    # Protect against decompression bomb attacks
    Image.MAX_IMAGE_PIXELS = 25_000_000
    img = Image.open(io.BytesIO(file_bytes))
    img = ImageOps.exif_transpose(img)
    # Composite transparent/alpha channels onto a solid white background
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        white_bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        white_bg.paste(rgba, (0, 0), rgba)
        return white_bg.convert("RGB")
    return img.convert("RGB")


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


def blocks_to_react_nodes(blocks, img_height=500, img_width=400, connections=None) -> list:
    nodes = []
    incoming = {str(connection["to"]) for connection in connections or []}
    outgoing = {str(connection["from"]) for connection in connections or []}
    for i, b in enumerate(blocks):
        shape_type = b.get("type", "process")
        text = b.get("text", "").strip()
        cx = b.get("center", (img_width // 2, (i + 1) * 100))[0]
        cy = b.get("center", (img_width // 2, (i + 1) * 100))[1]
        needs_review = bool(b.get("text_uncertain"))
        if not text:
            if shape_type == "start_end":
                if str(b["id"]) not in incoming and str(b["id"]) in outgoing:
                    text = "Start"
                elif str(b["id"]) in incoming and str(b["id"]) not in outgoing:
                    text = "End"
                else:
                    text = "Needs review: unread start/end"
                needs_review = True
            else:
                text = "Needs review: unread"
                needs_review = True

        x = int((cx / max(img_width, 1)) * 550) + 50
        y = int((cy / max(img_height, 1)) * 600) + 30
        nodes.append({
            "id": str(b["id"]),
            "type": NODE_TYPE_MAP.get(shape_type, "process"),
            "position": {"x": x, "y": y},
            "data": {
                "label": text,
                "needs_review": needs_review,
                "uncertain": needs_review,
                "confidence": b.get("text_confidence", -1),
            },
        })
    return nodes


def connections_to_react_edges(connections) -> list:
    edges = []
    ordered = sorted(
        connections,
        key=lambda c: (str(c["from"]), str(c["to"]), str(c.get("branch") or "")),
    )
    for i, c in enumerate(ordered):
        label = c.get("branch") or ""
        handle = "yes" if str(label).lower() in ("yes", "true") else ("no" if str(label).lower() in ("no", "false") else None)
        is_uncertain = bool(c.get("uncertain"))
        is_unconfirmed = bool(c.get("unconfirmed_suggestion"))
        e = {
            "id": f"e_{i}",
            "source": str(c["from"]),
            "target": str(c["to"]),
            "type": "smoothstep",
            "animated": True,
            "label": label,
            "style": {"strokeDasharray": "5,5"} if is_uncertain else {},
            "data": {
                "confidence": c.get("confidence", 1.0),
                "uncertain": is_uncertain,
                "unconfirmed_suggestion": is_unconfirmed,
            },
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
    {"id": "2", "type": "input_output", "position": {"x": 300, "y": 150}, "data": {"label": "Input n"}},
    {"id": "3", "type": "process", "position": {"x": 300, "y": 250}, "data": {"label": "i = 1"}},
    {"id": "4", "type": "decision", "position": {"x": 300, "y": 350}, "data": {"label": "i <= n?"}}
  ],
  "edges": [
    {"id": "e1-2", "source": "1", "target": "2", "type": "smoothstep", "animated": true, "label": ""},
    {"id": "e2-3", "source": "2", "target": "3", "type": "smoothstep", "animated": true, "label": ""},
    {"id": "e3-4", "source": "3", "target": "4", "type": "smoothstep", "animated": true, "label": ""},
    {"id": "e4-5", "source": "4", "target": "5", "sourceHandle": "yes", "type": "smoothstep", "animated": true, "label": "Yes"}
  ]
}

Allowed node types: start_end, process, input_output, decision, document, predefined_process, database, manual_input, connector, offpage, delay
- start_end: oval Start/End. Every flowchart MUST begin with Start and conclude at End.
- process: rectangle (assignments and calculations, e.g. "fact = 1", "fact = fact * i", "i = i + 1"). Never output no-op assignments like "fact = fact".
- input_output: parallelogram (e.g. "Input n", 'Print fact', 'Print "Even"').
- decision: diamond; MUST have exactly two outgoing edges labeled "Yes" and "No" with sourceHandle yes/no.
CRITICAL FLOWCHART LOGIC RULES:
1. Every variable used in a condition or calculation MUST be initialized or input in a preceding node (e.g. "i = 1", "fact = 1", "Input n") before it is read.
2. Every loop MUST include loop variable initialization before the decision AND a loop variable update (e.g. "i = i + 1") inside the loop body along the cycle back to the decision.
3. Always layout top-to-bottom around x=300. Merge non-loop branches into a shared End when they finish.
"""




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
            pil_img = pil_from_upload(img_bytes)
        elif file:
            contents = await file.read()
            if len(contents) > MAX_IMAGE_UPLOAD_SIZE:
                raise HTTPException(413, f"Uploaded image exceeds the {MAX_IMAGE_UPLOAD_SIZE // (1024 * 1024)}MB file size limit.")
            if len(contents) < 100:
                raise HTTPException(400, "Uploaded file appears to be empty or too small.")
            name = (file.filename or "").lower()
            if name and not any(name.endswith(ext) for ext in ALLOWED_IMAGE_EXTENSIONS):
                raise HTTPException(400, "Invalid image file. Please upload a PNG, JPG, JPEG, WEBP, or BMP.")
            try:
                pil_img = pil_from_upload(contents)
            except Exception:
                raise HTTPException(400, "Invalid image file. Could not decode image data.")
        else:
            raise HTTPException(400, "No image provided. Please upload a PNG, JPG, JPEG, WEBP, or BMP.")

        norm_img = cv_engine.normalize_image(pil_img)
        h, w = norm_img.shape[:2]
        logger.info("Image preprocessing complete: %dx%d", w, h)
        blocks, thresh = cv_engine.detect_symbols(norm_img)

        if not blocks:
            raise HTTPException(422, "No flowchart symbols detected. Please ensure the image contains clear shapes.")

        shape_counts = {}
        for block in blocks:
            shape_type = block.get("type", "unknown")
            shape_counts[shape_type] = shape_counts.get(shape_type, 0) + 1
        logger.info(
            "Shape detection complete: %d shapes (%s)",
            len(blocks),
            ", ".join(f"{shape_type}={count}" for shape_type, count in sorted(shape_counts.items())),
        )
        connections, connection_warnings = cv_engine.detect_connections(thresh, blocks)
        logger.info(
            "Connection reconstruction complete: %d directed connections, %d uncertain",
            len(connections),
            sum(bool(connection.get("uncertain")) for connection in connections),
        )

        ocr_failed = 0
        ocr_uncertain = 0
        for b in blocks:
            try:
                b["text"], b["text_confidence"] = ocr_engine.extract_block_text_with_confidence(
                    norm_img, b["bbox"]
                )
                b["text_uncertain"] = (
                    not b["text"] or b["text_confidence"] < OCR_REVIEW_CONFIDENCE
                )
                if not b["text"]:
                    ocr_failed += 1
                if b["text_uncertain"]:
                    ocr_uncertain += 1
                logger.debug(
                    "OCR shape #%s (%s): confidence %.1f, text=%r",
                    b["id"], b.get("type"), b["text_confidence"], b["text"],
                )
            except Exception as e:
                b["text"] = ""
                b["text_confidence"] = -1
                b["text_uncertain"] = True
                ocr_failed += 1
                ocr_uncertain += 1
                logger.warning("OCR failed for detected shape #%s: %s", b["id"], e)

        # Optional Gemini Vision OCR fallback if local OCR missed shapes and API key is present
        if ocr_failed > 0 and GEMINI_API_KEY:
            try:
                ai_texts = ocr_engine.extract_flowchart_text_with_gemini(pil_img, blocks, timeout_sec=6.0)
                if ai_texts:
                    for b in blocks:
                        bid = int(b["id"])
                        if not b.get("text") and bid in ai_texts and ai_texts[bid]:
                            b["text"] = ai_texts[bid]
                            b["text_uncertain"] = True
                            ocr_failed = max(0, ocr_failed - 1)
                            ocr_uncertain += 1
            except Exception as e:
                connection_warnings.append(f"AI vision OCR fell back to local recognition: {e}")

        # Branch label recognition for decision diamonds
        if ocr_engine.tesseract_available():
            blocks_by_id = {int(block["id"]): block for block in blocks}
            for connection in connections:
                start_block = blocks_by_id.get(int(connection["from"]))
                end_block = blocks_by_id.get(int(connection["to"]))
                if not start_block or start_block.get("type") != "decision" or connection.get("branch"):
                    continue

                points_to_check = []
                vec = connection.get("vector")
                if vec:
                    (vx1, vy1), (vx2, vy2) = vec
                    for frac in (0.2, 0.4, 0.6):
                        px = int(vx1 + (vx2 - vx1) * frac)
                        py = int(vy1 + (vy2 - vy1) * frac)
                        points_to_check.extend([(px, py), (px, py - 30), (px, py + 30)])

                bx, by, bw, bh = start_block["bbox"]
                cx, cy = start_block["center"]
                tcx, tcy = end_block["center"]

                if tcx < cx:
                    lx, ly = bx, by + bh // 2
                    points_to_check.extend([(lx - 45, ly - 30), (lx - 45, ly + 15), (lx - 30, ly - 35), (lx - 60, ly - 20)])
                if tcx > cx:
                    rx, ry = bx + bw, by + bh // 2
                    points_to_check.extend([(rx + 45, ry - 30), (rx + 45, ry + 15), (rx + 30, ry - 35), (rx + 60, ry - 20)])
                if tcy > cy:
                    botx, boty = bx + bw // 2, by + bh
                    points_to_check.extend([(botx - 30, boty + 30), (botx + 30, boty + 30)])

                for frac in (0.3, 0.5, 0.7):
                    points_to_check.append((int(cx + (tcx - cx) * frac), int(cy + (tcy - cy) * frac)))

                branch_candidates = []
                for px, py in points_to_check:
                    w_box, h_box = 80, 48
                    box = (px - w_box // 2, py - h_box // 2, w_box, h_box)
                    txt, conf = ocr_engine.extract_region_text_with_confidence(norm_img, box)
                    cleaned = ocr_engine.clean_branch_label(txt)
                    if cleaned in ("Yes", "No"):
                        branch_candidates.append((cleaned, conf))

                if branch_candidates:
                    chosen = max(branch_candidates, key=lambda c: c[1])[0]
                    connection["branch"] = chosen

        warnings = list(connection_warnings)

        # Decision branches suggestion logic - Requirement 2:
        # "Do not silently infer Yes/No branches. You may suggest a complementary branch label,
        # but mark it uncertain and require user confirmation before generating code."
        decision_ids = {str(block["id"]) for block in blocks if block.get("type") == "decision"}
        for decision_id in decision_ids:
            decision_edges = [edge for edge in connections if str(edge["from"]) == decision_id]
            if len(decision_edges) == 2:
                e1, e2 = decision_edges[0], decision_edges[1]
                b1 = e1.get("branch", "")
                b2 = e2.get("branch", "")
                if b1 in ("Yes", "No") and not b2:
                    comp = "No" if b1 == "Yes" else "Yes"
                    e2["branch"] = comp
                    e2["uncertain"] = True
                    e2["unconfirmed_suggestion"] = True
                    e2["confidence"] = 0.5
                    warnings.append(
                        f"Decision #{decision_id}: complementary branch label '{comp}' was suggested for path to shape #{e2['to']}; "
                        "it is marked uncertain and requires user confirmation before code generation."
                    )
                elif b2 in ("Yes", "No") and not b1:
                    comp = "No" if b2 == "Yes" else "Yes"
                    e1["branch"] = comp
                    e1["uncertain"] = True
                    e1["unconfirmed_suggestion"] = True
                    e1["confidence"] = 0.5
                    warnings.append(
                        f"Decision #{decision_id}: complementary branch label '{comp}' was suggested for path to shape #{e1['to']}; "
                        "it is marked uncertain and requires user confirmation before code generation."
                    )
                elif not b1 and not b2:
                    e1["uncertain"] = True
                    e2["uncertain"] = True
                    e1["confidence"] = min(float(e1.get("confidence", 1)), 0.5)
                    e2["confidence"] = min(float(e2.get("confidence", 1)), 0.5)
                    warnings.append(
                        f"Branch labels for decision #{decision_id} could not be detected; both connections are marked for review. "
                        "Please label the Yes and No branches."
                    )
            elif len(decision_edges) < 2:
                for edge in decision_edges:
                    edge["uncertain"] = True
                warnings.append(
                    f"Decision #{decision_id} has only {len(decision_edges)} outgoing branch; decisions require both Yes and No branches."
                )
            elif len(decision_edges) > 2:
                for edge in decision_edges:
                    edge["uncertain"] = True
                warnings.append(
                    f"Decision #{decision_id} has {len(decision_edges)} outgoing connections; review the branch structure."
                )

        overlay = cv_engine.overlay_detections(norm_img, blocks, connections)
        overlay_b64 = img_to_b64(overlay)

        react_nodes = blocks_to_react_nodes(blocks, img_height=h, img_width=w, connections=connections)
        react_edges = connections_to_react_edges(connections)

        blocks_json = [
            {"id": b["id"], "type": b["type"], "text": b["text"],
             "bbox": list(b["bbox"]), "center": list(b["center"])}
            for b in blocks
        ]
        connections_json = [
            {
                "from": c["from"],
                "to": c["to"],
                "branch": c.get("branch", ""),
                "confidence": c.get("confidence", 1.0),
                "uncertain": bool(c.get("uncertain")),
                "unconfirmed_suggestion": bool(c.get("unconfirmed_suggestion")),
            }
            for c in connections
        ]

        if not ocr_engine.tesseract_available():
            warnings.append(
                "Tesseract OCR is unavailable; node and branch labels could not be read. "
                "Install Tesseract OCR and retry, or review and edit the detected nodes manually."
            )
        elif ocr_failed:
            warnings.append(
                f"Could not read text from {ocr_failed} of {len(blocks)} detected shapes; marked as 'Needs review'. "
                "Please review and edit those node labels on the canvas before generating code."
            )
        if ocr_uncertain and ocr_uncertain > ocr_failed:
            warnings.append(
                f"OCR confidence is low for {ocr_uncertain - ocr_failed} detected shape label(s). "
                "Review and confirm those labels on the canvas before generating code."
            )

        connected_ids = {
            int(node_id)
            for edge in connections
            for node_id in (edge["from"], edge["to"])
        }
        missing_connections = [str(block["id"]) for block in blocks if int(block["id"]) not in connected_ids]
        for mid in missing_connections:
            warnings.append(f"Node #{mid} has no arrow connections.")

        has_uncertain_edges = any(bool(e.get("uncertain")) or bool(e.get("unconfirmed_suggestion")) for e in connections)
        has_needs_review_nodes = any(
            n.get("data", {}).get("needs_review") or n.get("data", {}).get("uncertain")
            for n in react_nodes
        )
        graph_status = "needs_review" if (has_uncertain_edges or has_needs_review_nodes or ocr_failed > 0 or missing_connections) else "verified"

        warning = " ".join(dict.fromkeys(warnings)) or None

        return JSONResponse({
            "nodes": react_nodes,
            "edges": react_edges,
            "blocks": blocks_json,
            "connections": connections_json,
            "overlay_image": overlay_b64,
            "warning": warning,
            "warnings": list(dict.fromkeys(warnings)),
            "graph_status": graph_status,
            "missing_connections": missing_connections,
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
        # Prefer the verified deterministic flowchart for standard teaching patterns to ensure
        # full algorithm correctness, avoid missing loop steps, and avoid quota limits.
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

        # Check for unreadable / 'Needs review' nodes (Requirement 1)
        needs_review_nodes = [
            node for node in nodes
            if (
                isinstance(node.get("data"), dict)
                and (node["data"].get("needs_review") or node["data"].get("uncertain"))
            )
            or logic_engine.node_text(node).lower().startswith("needs review")
            or "needs review" in logic_engine.node_text(node).lower()
            or logic_engine.node_text(node).lower().startswith("unlabeled")
            or not logic_engine.node_text(node).strip()
        ]
        if needs_review_nodes:
            raise HTTPException(
                422,
                "Some imported flowchart labels are unreadable or low-confidence and are marked 'Needs review'. "
                "Please correct and confirm these nodes on the canvas before generating code.",
            )

        # Check for unconfirmed suggested decision branches (Requirement 2)
        unconfirmed_edges = [
            edge for edge in edges
            if (isinstance(edge.get("data"), dict) and edge["data"].get("unconfirmed_suggestion"))
            or edge.get("unconfirmed_suggestion")
        ]
        if unconfirmed_edges:
            raise HTTPException(
                422,
                "Some decision branches have suggested labels that require user confirmation. "
                "Please review and confirm or edit the branch labels before generating code.",
            )

        # Check for uncertain arrow connections (Requirement 5)
        uncertain_edges = [
            edge for edge in edges
            if isinstance(edge.get("data"), dict) and edge["data"].get("uncertain")
        ]
        if uncertain_edges:
            raise HTTPException(
                422,
                "Some imported connections have uncertain arrow direction. "
                "Review or reconnect the dashed edges before generating Python.",
            )
        ast_data = logic_engine.build_flowchart_ast(nodes, edges)

        code = logic_engine.compile_to_python(ast_data)

        try:
            py_ast.parse(code)
        except SyntaxError as se:
            raise HTTPException(
                422,
                f"The current flowchart could not be translated to valid Python: {se.msg} (line {se.lineno}).",
            )

        undefined = logic_engine._undefined_identifiers(code)
        if undefined:
            vars_str = ", ".join(sorted(repr(u) for u in undefined))
            raise HTTPException(
                422,
                f"Flowchart is incomplete: variable(s) {vars_str} are used in conditions or operations but never defined or initialized. "
                "Add an initialization step (e.g. an assignment or input node) on the canvas before generating code.",
            )

        warnings = list(logic_engine.consistency_warnings(ast_data, code))
        return JSONResponse({
            "code": code,
            "ast": ast_data,
            "source": "compiler",
            "warnings": warnings,
        })
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(422, f"The current flowchart cannot be compiled safely: {str(e)}")
    except Exception as e:
        raise HTTPException(500, f"Code generation failed: {str(e)}")


@app.post("/api/execute")
async def execute_code(request: Request, request_body: dict):
    try:
        raw_code = request_body.get("code") or ""
        user_input = request_body.get("user_input", "")
        if user_input is None:
            user_input = ""
        if not isinstance(raw_code, str) or not isinstance(user_input, str):
            raise HTTPException(422, "Both 'code' and 'user_input' must be strings.")
        code = raw_code.strip()
        if not code:
            raise HTTPException(400, "No code to execute. Generate Python from your flowchart first.")

        # Blocking work (sandbox + subprocess) runs in the thread pool so it cannot freeze the server.
        result = await run_in_threadpool(executor.execute, code, user_input, 5, _request_is_local(request))
        if result.status == "disabled":
            raise HTTPException(403, result.message)
        if result.status == "busy":
            raise HTTPException(429, result.message, headers={"Retry-After": "2"})
        if result.status == "too_large":
            raise HTTPException(413, result.message)

        output_text = result.legacy_output()
        status = "success" if result.success else "error"
        stdout = "" if result.status == "rejected" else output_text
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
            # additive fields (the original contract above is unchanged)
            "timed_out": result.timed_out,
            "truncated": result.truncated,
            "execution_mode": result.mode,
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
        try:
            ast_data = logic_engine.build_flowchart_ast(nodes, edges)
            code = logic_engine.compile_to_python(ast_data)
            undefined = logic_engine._undefined_identifiers(code)
            if undefined:
                vars_str = ", ".join(sorted(repr(u) for u in undefined))
                return JSONResponse({
                    "reply": f"The flowchart is incomplete: variable(s) {vars_str} are used in conditions or operations but never defined or initialized. Add an initialization step on the canvas first.",
                    "patch": None,
                    "trigger": None,
                    "error": True,
                })
        except ValueError as ve:
            return JSONResponse({
                "reply": f"Could not generate code: {str(ve)}",
                "patch": None,
                "trigger": None,
                "error": True,
            })
        return JSONResponse({
            "reply": "Generated Python from the current flowchart. It is now in the code panel.",
            "patch": None,
            "trigger": "generate_code",
            "code": code,
            "source": "compiler",
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


DIST_DIR = Path(__file__).resolve().parent / "landing" / "dist"


def _json_not_found(detail: str = "Not Found") -> JSONResponse:
    return JSONResponse({"detail": detail}, status_code=404)


def _safe_dist_file(relative: str) -> Optional[Path]:
    """Return a regular file strictly inside DIST_DIR, or None.

    The original handler joined the raw URL path onto DIST_DIR, so a request such as
    /%2e%2e/%2e%2e/.env served files outside the build folder (including .env).
    Here the path is fully resolved (this follows symlinks and '..') and must still be
    inside DIST_DIR. Dot-files and dot-directories are never served.
    """
    if "\x00" in relative or "\\" in relative:
        return None
    if any(part.startswith(".") for part in relative.split("/") if part):
        return None
    try:
        root = DIST_DIR.resolve()
        candidate = (root / relative).resolve()
        candidate.relative_to(root)
    except (ValueError, OSError, RuntimeError):
        return None
    return candidate if candidate.is_file() else None


# Any /api/* path that no route above handled is a JSON 404, never the frontend HTML.
@app.api_route(
    "/api/{rest:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"],
    include_in_schema=False,
)
async def api_not_found(rest: str):
    return _json_not_found()


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str):
    if not DIST_DIR.is_dir():
        return _json_not_found("Frontend build not found. Run 'npm run build' in the landing folder.")
    # Reject dot-files and traversal attempts with 404, never serve them.
    if any(part.startswith(".") for part in full_path.split("/") if part):
        return _json_not_found()
    file_path = _safe_dist_file(full_path)
    if file_path is not None:
        headers = {"Cache-Control": "public, max-age=31536000, immutable"} if full_path.startswith("assets/") else None
        return FileResponse(str(file_path), headers=headers)
    # Missing assets and anything that looks like a file must 404, not return index.html.
    last_segment = full_path.rsplit("/", 1)[-1]
    if full_path.startswith("assets/") or "." in last_segment:
        return _json_not_found()
    index = _safe_dist_file("index.html")
    if index is None:
        return _json_not_found("Frontend build not found. Run 'npm run build' in the landing folder.")
    return FileResponse(str(index))

    return JSONResponse({"detail": "Not found"}, status_code=404)
