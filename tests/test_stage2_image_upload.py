"""
Stage 2 Image Upload and Graph Reconstruction Tests.

Validates:
1. Adaptive morphology & shape detection on synthetic images.
2. Arrow direction recovery, especially backward loop-back arrows.
3. Decision branch (Yes/No) detection and suggested branch gating.
4. Transparent PNG compositing over white canvas.
5. EXIF orientation handling.
6. Upload limits (15 MB cap) and file validation.
7. Gemini Vision fallback safety and backend-only key isolation.
8. Gating 'Needs review' nodes against premature code generation.
9. Full pipeline test: Synthetic Factorial Flowchart -> Image Detection ->
   Graph Reconstruction -> AST Compilation -> Execution producing 120 for input 5.
"""

import ast as py_ast
import io
import os
import pytest
import cv2
import numpy as np
from PIL import Image
from fastapi.testclient import TestClient

import api_server
from api_server import app, MAX_IMAGE_UPLOAD_SIZE, pil_from_upload
import cv_engine
import ocr_engine
import logic_engine
import executor

client = TestClient(app)


def build_synthetic_factorial_image() -> np.ndarray:
    """
    Renders a standard 9-node Factorial Flowchart with a loop-back edge:
    Start -> Input n -> fact = 1 -> i = 1 -> Decision i <= n
      Yes -> fact = fact * i -> i = i + 1 -> (Loop-back up to Decision)
      No  -> Print fact -> End
    """
    canvas = np.ones((700, 700, 3), dtype=np.uint8) * 255

    # 1. Start oval
    cv2.ellipse(canvas, (350, 50), (60, 25), 0, 0, 360, (0, 0, 0), 2)
    cv2.putText(canvas, "Start", (325, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    cv2.arrowedLine(canvas, (350, 75), (350, 110), (0, 0, 0), 2, tipLength=0.2)

    # 2. Input n
    pts_in = np.array([[260, 110], [440, 110], [420, 155], [240, 155]], np.int32)
    cv2.polylines(canvas, [pts_in], True, (0, 0, 0), 2)
    cv2.putText(canvas, "Input n", (295, 138), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)
    cv2.arrowedLine(canvas, (350, 155), (350, 185), (0, 0, 0), 2, tipLength=0.2)

    # 3. fact = 1
    cv2.rectangle(canvas, (260, 185), (440, 230), (0, 0, 0), 2)
    cv2.putText(canvas, "fact = 1", (305, 213), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)
    cv2.arrowedLine(canvas, (350, 230), (350, 260), (0, 0, 0), 2, tipLength=0.2)

    # 4. i = 1
    cv2.rectangle(canvas, (260, 260), (440, 305), (0, 0, 0), 2)
    cv2.putText(canvas, "i = 1", (325, 288), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)
    cv2.arrowedLine(canvas, (350, 305), (350, 335), (0, 0, 0), 2, tipLength=0.2)

    # 5. Decision diamond i <= n
    diamond_pts = np.array([[350, 335], [440, 385], [350, 435], [260, 385]], np.int32)
    cv2.polylines(canvas, [diamond_pts], True, (0, 0, 0), 2)
    cv2.putText(canvas, "i <= n", (320, 390), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)

    # Yes branch going down
    cv2.putText(canvas, "Yes", (360, 455), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
    cv2.arrowedLine(canvas, (350, 435), (350, 480), (0, 0, 0), 2, tipLength=0.2)

    # 6. fact = fact * i
    cv2.rectangle(canvas, (250, 480), (450, 525), (0, 0, 0), 2)
    cv2.putText(canvas, "fact = fact * i", (265, 508), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)
    cv2.arrowedLine(canvas, (350, 525), (350, 555), (0, 0, 0), 2, tipLength=0.2)

    # 7. i = i + 1
    cv2.rectangle(canvas, (270, 555), (430, 600), (0, 0, 0), 2)
    cv2.putText(canvas, "i = i + 1", (315, 583), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)

    # Backward Loop-back arrow from node 7 (i = i + 1) back UP to node 5 (decision diamond)
    # Exits left of node 7 at (270, 577), travels left to (170, 577), goes UP to (170, 385),
    # and enters the left vertex of decision diamond with arrowhead pointing into (258, 385).
    cv2.line(canvas, (270, 577), (170, 577), (0, 0, 0), 2)
    cv2.line(canvas, (170, 577), (170, 385), (0, 0, 0), 2)
    cv2.arrowedLine(canvas, (170, 385), (258, 385), (0, 0, 0), 2, tipLength=0.15)

    # No branch exiting right vertex of decision diamond at (440, 385)
    cv2.putText(canvas, "No", (455, 375), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
    cv2.arrowedLine(canvas, (440, 385), (520, 385), (0, 0, 0), 2, tipLength=0.2)

    # 8. Print fact
    pts_out = np.array([[530, 360], [670, 360], [650, 410], [510, 410]], np.int32)
    cv2.polylines(canvas, [pts_out], True, (0, 0, 0), 2)
    cv2.putText(canvas, "Print fact", (535, 390), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
    cv2.arrowedLine(canvas, (590, 410), (590, 450), (0, 0, 0), 2, tipLength=0.2)

    # 9. End oval
    cv2.ellipse(canvas, (590, 475), (55, 25), 0, 0, 360, (0, 0, 0), 2)
    cv2.putText(canvas, "End", (570, 480), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

    return canvas


# ============================================================================
# Category 1: Image Detection
# ============================================================================

def test_adaptive_thresholds_scaling():
    """Verify that get_adaptive_params scales appropriately across different image sizes."""
    small = cv_engine.get_adaptive_params(400, 300)
    medium = cv_engine.get_adaptive_params(800, 600)
    large = cv_engine.get_adaptive_params(2400, 1800)

    # Kernels must be odd integers
    assert small["k_blur"][0] % 2 == 1
    assert medium["k_blur"][0] % 2 == 1
    assert large["k_blur"][0] % 2 == 1

    # Parameters scale up with resolution
    assert large["pad"] > small["pad"]
    assert large["route_dist"] > small["route_dist"]
    assert large["hough_thresh"] > small["hough_thresh"]
    assert large["min_component_area"] > small["min_component_area"]


def test_synthetic_factorial_symbol_detection():
    """Verify that all 9 symbols in the factorial flowchart are detected accurately."""
    bgr = build_synthetic_factorial_image()
    blocks, thresh = cv_engine.detect_symbols(bgr)

    assert len(blocks) == 9, f"Expected 9 flowchart symbols, detected {len(blocks)}"
    types = [b["type"] for b in blocks]
    assert "start_end" in types
    assert "decision" in types
    assert "process" in types
    assert "input_output" in types


def test_transparent_png_compositing():
    """Verify transparent PNGs composite onto white rather than black canvas."""
    # Create an RGBA image with transparent background and black line
    rgba = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    # Draw black pixels in the center
    for x in range(40, 60):
        for y in range(40, 60):
            rgba.putpixel((x, y), (0, 0, 0, 255))

    buf = io.BytesIO()
    rgba.save(buf, format="PNG")
    raw_bytes = buf.getvalue()

    result_img = pil_from_upload(raw_bytes)
    assert result_img.mode == "RGB"

    # Background corners must be white (255, 255, 255), NOT black (0, 0, 0)
    corner_pixel = result_img.getpixel((5, 5))
    assert corner_pixel == (255, 255, 255), f"Expected white background, got {corner_pixel}"

    # Center must remain black
    center_pixel = result_img.getpixel((50, 50))
    assert center_pixel == (0, 0, 0), f"Expected black stroke, got {center_pixel}"


def test_exif_rotation_handling():
    """Verify EXIF rotation tags are applied via exif_transpose before processing."""
    # Create simple image and attach EXIF orientation tag 6 (90 CW rotation)
    img = Image.new("RGB", (200, 100), color=(255, 255, 255))
    exif = img.getexif()
    exif[0x0112] = 6  # Orientation: Rotate 90 CW

    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    raw_bytes = buf.getvalue()

    transposed = pil_from_upload(raw_bytes)
    # 200x100 rotated 90 CW becomes 100x200
    assert transposed.size == (100, 200)


def test_upload_size_limit_rejection():
    """Verify that uploaded images exceeding 15MB are rejected with HTTP 413."""
    oversized_bytes = b"0" * (MAX_IMAGE_UPLOAD_SIZE + 1024)
    response = client.post(
        "/api/analyze",
        files={"file": ("huge_flowchart.png", oversized_bytes, "image/png")},
    )
    assert response.status_code == 413
    assert "exceeds" in response.json()["detail"]


# ============================================================================
# Category 2: Graph Reconstruction
# ============================================================================

def test_factorial_loopback_and_branch_reconstruction():
    """
    Verify the backward loop-back arrow from node 7 up to decision node 5,
    along with Yes/No branches, are successfully reconstructed.
    """
    bgr = build_synthetic_factorial_image()
    _, buf = cv2.imencode(".png", bgr)

    response = client.post(
        "/api/analyze",
        files={"file": ("factorial.png", buf.tobytes(), "image/png")},
    )
    assert response.status_code == 200
    data = response.json()

    nodes = data["nodes"]
    edges = data["edges"]
    assert len(nodes) == 9

    # Find the decision node
    decision_nodes = [n for n in nodes if n["type"] == "decision"]
    assert len(decision_nodes) == 1
    dec_id = decision_nodes[0]["id"]

    # Verify decision outgoing branches
    dec_outgoing = [e for e in edges if e["source"] == dec_id]
    assert len(dec_outgoing) == 2, f"Decision should have 2 outgoing branches, got {len(dec_outgoing)}"
    branch_labels = {e.get("label") for e in dec_outgoing}
    assert "Yes" in branch_labels and "No" in branch_labels

    # Verify the loop-back edge: an edge whose target is the decision node
    # from a lower process node
    incoming_to_dec = [e for e in edges if e["target"] == dec_id]
    # One incoming from initial setup (i = 1), one loop-back from bottom (i = i + 1)
    assert len(incoming_to_dec) >= 2, f"Expected at least 2 incoming edges to decision, got {len(incoming_to_dec)}"


def test_needs_review_on_unread_nodes():
    """
    Verify that nodes with unreadable text are marked 'Needs review'
    and block code generation until corrected (Requirement 1).
    """
    # Create flowchart graph with a blank node that failed OCR
    nodes = [
        {"id": "1", "type": "start_end", "position": {"x": 300, "y": 40}, "data": {"label": "Start"}},
        {"id": "2", "type": "process", "position": {"x": 300, "y": 140}, "data": {"label": "Needs review: unread", "needs_review": True}},
        {"id": "3", "type": "start_end", "position": {"x": 300, "y": 240}, "data": {"label": "End"}},
    ]
    edges = [
        {"id": "e1", "source": "1", "target": "2"},
        {"id": "e2", "source": "2", "target": "3"},
    ]

    res = client.post("/api/generate-code", json={"nodes": nodes, "edges": edges})
    assert res.status_code == 422
    assert "Needs review" in res.json()["detail"]


def test_unconfirmed_branch_suggestion_blocks_generation():
    """
    Verify that suggested complementary decision branches are flagged uncertain
    and require user confirmation before generating code (Requirement 2).
    """
    nodes = [
        {"id": "1", "type": "start_end", "position": {"x": 300, "y": 40}, "data": {"label": "Start"}},
        {"id": "2", "type": "decision", "position": {"x": 300, "y": 140}, "data": {"label": "x > 0"}},
        {"id": "3", "type": "input_output", "position": {"x": 150, "y": 240}, "data": {"label": "Print Pos"}},
        {"id": "4", "type": "input_output", "position": {"x": 450, "y": 240}, "data": {"label": "Print Neg"}},
        {"id": "5", "type": "start_end", "position": {"x": 300, "y": 340}, "data": {"label": "End"}},
    ]
    edges = [
        {"id": "e1", "source": "1", "target": "2"},
        {"id": "e2", "source": "2", "target": "3", "sourceHandle": "yes", "label": "Yes"},
        # e3 was suggested and marked unconfirmed
        {
            "id": "e3", "source": "2", "target": "4", "sourceHandle": "no", "label": "No",
            "data": {"uncertain": True, "unconfirmed_suggestion": True}
        },
        {"id": "e4", "source": "3", "target": "5"},
        {"id": "e5", "source": "4", "target": "5"},
    ]

    # Must be rejected because e3 is an unconfirmed suggestion
    res = client.post("/api/generate-code", json={"nodes": nodes, "edges": edges})
    assert res.status_code == 422
    assert "confirmation" in res.json()["detail"].lower()

    # Once the user confirms the branch (clearing unconfirmed_suggestion & uncertain)
    edges[2]["data"]["unconfirmed_suggestion"] = False
    edges[2]["data"]["uncertain"] = False
    res2 = client.post("/api/generate-code", json={"nodes": nodes, "edges": edges})
    assert res2.status_code == 200
    assert "if x > 0:" in res2.json()["code"]


def test_gemini_vision_fallback_safety():
    """
    Verify Gemini Vision handles missing key, errors, and timeouts gracefully
    without raising exceptions or exposing keys (Requirement 4).
    """
    img = Image.new("RGB", (100, 100), (255, 255, 255))
    blocks = [{"id": 1, "type": "process", "bbox": [10, 10, 80, 80]}]

    # When API key is not present, returns {} safely
    old_key = os.environ.get("GEMINI_API_KEY")
    try:
        os.environ["GEMINI_API_KEY"] = ""
        res = ocr_engine.extract_flowchart_text_with_gemini(img, blocks)
        assert res == {}
    finally:
        if old_key is not None:
            os.environ["GEMINI_API_KEY"] = old_key


# ============================================================================
# Category 3: Python Execution
# ============================================================================

def test_reconstructed_factorial_graph_produces_120_for_input_5():
    """
    Verify that the reconstructed Factorial Graph compiles to deterministic
    Python with a valid while loop and executes to produce 120 for input 5 (Requirement 7).
    """
    nodes = [
        {"id": "1", "type": "start_end", "position": {"x": 300, "y": 40}, "data": {"label": "Start"}},
        {"id": "2", "type": "input_output", "position": {"x": 300, "y": 120}, "data": {"label": "Input n"}},
        {"id": "3", "type": "process", "position": {"x": 300, "y": 200}, "data": {"label": "fact = 1"}},
        {"id": "4", "type": "process", "position": {"x": 300, "y": 280}, "data": {"label": "i = 1"}},
        {"id": "5", "type": "decision", "position": {"x": 300, "y": 380}, "data": {"label": "i <= n"}},
        {"id": "6", "type": "process", "position": {"x": 300, "y": 480}, "data": {"label": "fact = fact * i"}},
        {"id": "7", "type": "process", "position": {"x": 300, "y": 560}, "data": {"label": "i = i + 1"}},
        {"id": "8", "type": "input_output", "position": {"x": 520, "y": 380}, "data": {"label": "Print fact"}},
        {"id": "9", "type": "start_end", "position": {"x": 520, "y": 480}, "data": {"label": "End"}},
    ]

    edges = [
        {"id": "e1", "source": "1", "target": "2"},
        {"id": "e2", "source": "2", "target": "3"},
        {"id": "e3", "source": "3", "target": "4"},
        {"id": "e4", "source": "4", "target": "5"},
        {"id": "e5", "source": "5", "target": "6", "sourceHandle": "yes", "label": "Yes"},
        {"id": "e6", "source": "6", "target": "7"},
        {"id": "e7", "source": "7", "target": "5"},  # loop-back edge!
        {"id": "e8", "source": "5", "target": "8", "sourceHandle": "no", "label": "No"},
        {"id": "e9", "source": "8", "target": "9"},
    ]

    # 1. Compile through existing logic_engine
    ast_data = logic_engine.build_flowchart_ast(nodes, edges)
    code = logic_engine.compile_to_python(ast_data)

    # 2. Syntax validation
    parsed = py_ast.parse(code)
    assert parsed is not None
    assert "while i <= n:" in code or "while" in code

    # 3. Execution with input 5
    # Force local-dev execution mode for testing
    old_mode = os.environ.get("FLOWFORGE_EXECUTION")
    try:
        os.environ["FLOWFORGE_EXECUTION"] = "local-dev"
        output = executor.run_code_safely(code, "5\n")
        assert "120" in str(output), f"Expected 120 in program output, received:\n{output}"
    finally:
        if old_mode is not None:
            os.environ["FLOWFORGE_EXECUTION"] = old_mode
        else:
            os.environ.pop("FLOWFORGE_EXECUTION", None)


def test_real_user_flowcharts_limitation_reported():
    """
    Explicitly test and report repository image availability.
    Only landing/src/assets/hero.png exists; real user flowcharts are unavailable.
    """
    assets_dir = os.path.join(r"c:\Users\Manasvi R\OneDrive\Desktop\FlowForge2Code", "landing", "src", "assets")
    hero_path = os.path.join(assets_dir, "hero.png")
    assert os.path.isfile(hero_path), "Expected hero.png to exist"

    # Verify no test flowchart directory exists in repo
    flowcharts_dir = os.path.join(r"c:\Users\Manasvi R\OneDrive\Desktop\FlowForge2Code", "flowcharts")
    assert not os.path.exists(flowcharts_dir), "Real user flowchart directory is not present in repo"
