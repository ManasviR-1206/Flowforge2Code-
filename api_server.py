"""
FlowForge AI – Unified FastAPI Backend
Serves the React landing+workspace SPA and exposes REST API endpoints
for the flowchart-to-code pipeline (CV, OCR, Logic, LLM, Executor).
"""

import base64
import io
import json
import os
import sys
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from PIL import Image

# ── Import our pipeline modules ──────────────────────────────────────────────
import cv_engine
import ocr_engine
import logic_engine
import llm_generator
import executor

from database import engine, Base, get_db
import models
from sqlalchemy.orm import Session
from fastapi import Depends

# ── App setup ────────────────────────────────────────────────────────────────
app = FastAPI(title="FlowForge AI API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)

@app.on_event("startup")
def create_default_user():
    db = next(get_db())
    if not db.query(models.User).filter_by(username="manasvi_r").first():
        user = models.User(username="manasvi_r", email="test@flowforge.ai")
        db.add(user)
        db.commit()

# ── Helper ────────────────────────────────────────────────────────────────────

def pil_from_upload(file_bytes: bytes) -> Image.Image:
    return Image.open(io.BytesIO(file_bytes)).convert("RGB")


def img_to_b64(cv_img: np.ndarray) -> str:
    """Encode a BGR numpy array to base64 PNG string for JSON transport."""
    _, buf = cv2.imencode(".png", cv_img)
    return base64.b64encode(buf).decode("utf-8")


def generate_sample_flowchart_cv() -> np.ndarray:
    """Return the same sample flowchart that the old Streamlit app used."""
    canvas = np.ones((500, 400, 3), dtype=np.uint8) * 255
    cv2.ellipse(canvas, (200, 50), (60, 25), 0, 0, 360, (0, 180, 0), 2)
    cv2.putText(canvas, "Start", (180, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 180, 0), 2)
    cv2.arrowedLine(canvas, (200, 75), (200, 120), (0, 0, 0), 2, tipLength=0.2)
    pts = np.array([[130, 120], [270, 120], [240, 160], [100, 160]], np.int32)
    cv2.polylines(canvas, [pts], True, (255, 0, 255), 2)
    cv2.putText(canvas, "Input n", (150, 145), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2)
    cv2.arrowedLine(canvas, (200, 160), (200, 210), (0, 0, 0), 2, tipLength=0.2)
    d_pts = np.array([[200, 210], [270, 250], [200, 290], [130, 250]], np.int32)
    cv2.polylines(canvas, [d_pts], True, (0, 200, 200), 2)
    cv2.putText(canvas, "n > 0?", (175, 255), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 150, 150), 2)
    cv2.arrowedLine(canvas, (200, 290), (200, 340), (0, 0, 0), 2, tipLength=0.2)
    cv2.putText(canvas, "Yes", (210, 315), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)
    o_pts = np.array([[130, 340], [270, 340], [240, 380], [100, 380]], np.int32)
    cv2.polylines(canvas, [o_pts], True, (255, 0, 255), 2)
    cv2.putText(canvas, "Print Positive", (135, 365), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 0, 255), 2)
    cv2.arrowedLine(canvas, (200, 380), (200, 430), (0, 0, 0), 2, tipLength=0.2)
    cv2.ellipse(canvas, (200, 455), (60, 25), 0, 0, 360, (0, 0, 255), 2)
    cv2.putText(canvas, "End", (185, 460), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
    return canvas  # BGR


# ── API Endpoints ─────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "FlowForge AI API"}


@app.post("/api/analyze")
async def analyze(
    file: Optional[UploadFile] = File(None),
    mode: str = Form("upload"),
    canvas_data: Optional[str] = Form(None),
):
    """
    Step 1+2: Receive flowchart image, run CV symbol detection + OCR.
    Returns detected blocks, connections, and overlay image (base64).
    """
    try:
        if mode == "sample":
            cv_bgr = generate_sample_flowchart_cv()
            pil_img = Image.fromarray(cv2.cvtColor(cv_bgr, cv2.COLOR_BGR2RGB))
        elif mode == "canvas" and canvas_data:
            img_bytes = base64.b64decode(canvas_data.split(",")[-1])
            pil_img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
        elif file:
            contents = await file.read()
            pil_img = pil_from_upload(contents)
        else:
            raise HTTPException(400, "No image provided.")

        norm_img = cv_engine.normalize_image(pil_img)
        blocks, thresh = cv_engine.detect_symbols(norm_img)
        connections = cv_engine.detect_connections(thresh, blocks)

        for b in blocks:
            b["text"] = ocr_engine.extract_block_text(norm_img, b["bbox"])

        overlay = cv_engine.overlay_detections(norm_img, blocks, connections)
        overlay_b64 = img_to_b64(overlay)

        blocks_json = []
        for b in blocks:
            blocks_json.append({
                "id": b["id"],
                "type": b["type"],
                "text": b["text"],
                "bbox": list(b["bbox"]),
                "center": list(b["center"]),
            })
        connections_json = [
            {"from": c["from"], "to": c["to"]} for c in connections
        ]

        return JSONResponse({
            "blocks": blocks_json,
            "connections": connections_json,
            "overlay_image": overlay_b64,
        })
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Analysis failed: {str(e)}")


@app.post("/api/generate")
async def generate(request_body: dict):
    """
    Step 3+4: Accept edited blocks+connections, build AST, generate Python code.
    Body: { blocks, connections, api_key? }
    """
    try:
        blocks = request_body.get("blocks", [])
        connections = request_body.get("connections", [])
        api_key = request_body.get("api_key", "")

        for b in blocks:
            if isinstance(b.get("bbox"), list):
                b["bbox"] = tuple(b["bbox"])

        ast = logic_engine.build_flowchart_ast(blocks, connections)
        code = llm_generator.generate_python_code(ast, api_key if api_key else None)

        return JSONResponse({"code": code, "ast": ast})
    except Exception as e:
        raise HTTPException(500, f"Code generation failed: {str(e)}")


@app.post("/api/run")
async def run_code(request_body: dict):
    """
    Step 5: Execute generated Python code in safe sandbox.
    Body: { code, user_input? }
    """
    try:
        code = request_body.get("code", "")
        user_input = request_body.get("user_input", "")
        output = executor.run_code_safely(code, user_input, timeout_sec=3)
        return JSONResponse({"output": output})
    except Exception as e:
        raise HTTPException(500, f"Execution failed: {str(e)}")

# ── Data Persistence Endpoints ──────────────────────────────────────────────

@app.post("/api/projects")
def save_project(request_body: dict, db: Session = Depends(get_db)):
    user = db.query(models.User).filter_by(username="manasvi_r").first()
    project = models.Project(
        name=request_body.get("name", "Untitled"),
        flowchart_data=json.dumps({"nodes": request_body.get("nodes", []), "edges": request_body.get("edges", [])}),
        generated_code=request_body.get("code", ""),
        user_id=user.id
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return {"status": "success", "project_id": project.id}

@app.get("/api/projects")
def list_projects(db: Session = Depends(get_db)):
    user = db.query(models.User).filter_by(username="manasvi_r").first()
    if not user:
        return []
    projects = db.query(models.Project).filter_by(user_id=user.id).order_by(models.Project.updated_at.desc()).all()
    return [{
        "id": p.id,
        "name": p.name,
        "updated_at": p.updated_at.isoformat() if p.updated_at else "",
        "created_at": p.created_at.isoformat() if p.created_at else ""
    } for p in projects]

@app.get("/api/projects/{project_id}")
def get_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")
    data = json.loads(project.flowchart_data) if project.flowchart_data else {"nodes": [], "edges": []}
    return {
        "id": project.id,
        "name": project.name,
        "nodes": data.get("nodes", []),
        "edges": data.get("edges", []),
        "generated_code": project.generated_code or "",
        "created_at": project.created_at.isoformat() if project.created_at else ""
    }

@app.delete("/api/projects/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(models.Project).filter_by(id=project_id).first()
    if not project:
        raise HTTPException(404, "Project not found")
    db.delete(project)
    db.commit()
    return {"status": "success", "message": "Project deleted"}

@app.post("/api/keys")
def generate_api_key(request_body: dict, db: Session = Depends(get_db)):
    user = db.query(models.User).filter_by(username="manasvi_r").first()
    if not user:
        user = models.User(username="manasvi_r", email="test@flowforge.ai")
        db.add(user)
        db.commit()
        db.refresh(user)
    import secrets
    new_key = f"ff_{secrets.token_hex(16)}"
    api_key = models.ApiKey(
        key=new_key,
        name=request_body.get("name", "New API Key"),
        user_id=user.id
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return {
        "status": "success", 
        "id": api_key.id,
        "key": new_key, 
        "name": api_key.name,
        "is_active": api_key.is_active,
        "created_at": api_key.created_at.isoformat() if api_key.created_at else ""
    }

@app.get("/api/keys")
def list_api_keys(db: Session = Depends(get_db)):
    user = db.query(models.User).filter_by(username="manasvi_r").first()
    if not user:
        return []
    keys = db.query(models.ApiKey).filter_by(user_id=user.id).order_by(models.ApiKey.created_at.desc()).all()
    return [{
        "id": k.id,
        "name": k.name,
        "key": k.key,
        "is_active": k.is_active,
        "created_at": k.created_at.isoformat() if k.created_at else ""
    } for k in keys]

@app.delete("/api/keys/{key_id}")
def revoke_api_key(key_id: str, db: Session = Depends(get_db)):
    key = db.query(models.ApiKey).filter_by(id=key_id).first()
    if not key:
        raise HTTPException(404, "API Key not found")
    db.delete(key)
    db.commit()
    return {"status": "success", "message": "API key revoked"}

@app.put("/api/keys/{key_id}/toggle")
def toggle_api_key(key_id: str, db: Session = Depends(get_db)):
    key = db.query(models.ApiKey).filter_by(id=key_id).first()
    if not key:
        raise HTTPException(404, "API Key not found")
    key.is_active = not key.is_active
    db.commit()
    return {"status": "success", "is_active": key.is_active}



# ── Serve React SPA (production build) ───────────────────────────────────────
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
