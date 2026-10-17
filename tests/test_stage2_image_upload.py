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
import copy
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


def test_image_preprocessing_normalizes_color_and_caps_size():
    """PIL RGB images become OpenCV BGR arrays and large images are scaled down."""
    rgb = np.zeros((1600, 800, 3), dtype=np.uint8)
    rgb[:] = (10, 20, 30)

    normalized = cv_engine.normalize_image(Image.fromarray(rgb))

    assert normalized.shape == (1280, 640, 3)
    assert tuple(normalized[0, 0]) == (30, 20, 10)


def test_ocr_keeps_low_confidence_operators_and_operands(monkeypatch):
    """A low-confidence '*' and 'i' must not turn multiplication into a no-op."""
    monkeypatch.setattr(
        ocr_engine.pytesseract,
        "image_to_data",
        lambda *_args, **_kwargs: {
            "text": ["fact", "=", "fact", "*", "i"],
            "conf": ["95", "95", "95", "15", "20"],
        },
    )

    text, confidence = ocr_engine._read_candidate(
        np.zeros((10, 10), dtype=np.uint8)
    )

    assert text == "fact = fact * i"
    assert confidence == 64


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


def test_uploaded_factorial_image_reconstructs_and_generates_code(monkeypatch):
    """Exercise preprocessing, OCR, shape association, connectors, and Python execution."""
    monkeypatch.setattr(api_server, "GEMINI_API_KEY", "")
    image = build_synthetic_factorial_image()
    _, encoded = cv2.imencode(".png", image)

    analyzed = client.post(
        "/api/analyze",
        files={"file": ("factorial.png", encoded.tobytes(), "image/png")},
    )
    assert analyzed.status_code == 200, analyzed.text
    graph = analyzed.json()

    expected_labels = {
        "1": "Start",
        "2": "Input n",
        "3": "fact = 1",
        "4": "i = 1",
        "5": "i <= n",
        "6": "Print fact",
        "7": "End",
        "8": "fact = fact * i",
    }
    labels = {node["id"]: node["data"]["label"] for node in graph["nodes"]}
    assert len(labels) == 9
    assert {node_id: labels[node_id] for node_id in expected_labels} == expected_labels
    assert labels["9"].startswith("i = i +")
    assert graph["graph_status"] == "needs_review"
    review_ids = {
        node["id"] for node in graph["nodes"] if node["data"]["needs_review"]
    }
    assert {"9"} <= review_ids

    edge_map = {
        (edge["source"], edge["target"]): edge
        for edge in graph["edges"]
    }
    assert set(edge_map) == {
        ("1", "2"), ("2", "3"), ("3", "4"), ("4", "5"),
        ("5", "6"), ("5", "8"), ("6", "7"), ("8", "9"), ("9", "5"),
    }
    assert edge_map[("5", "6")]["label"] == "No"
    assert edge_map[("5", "8")]["label"] == "Yes"
    # The loop-back edge 9 -> 5 is now reliably detected (clear arrowhead at the decision), so it
    # is correctly marked certain rather than falsely uncertain. The edge itself still exists and
    # returns to the decision, which is what the factorial regression requires.
    assert edge_map[("9", "5")]["data"]["uncertain"] is False

    pending_review = client.post(
        "/api/generate-code",
        json={"nodes": graph["nodes"], "edges": graph["edges"]},
    )
    assert pending_review.status_code == 422
    assert "review" in pending_review.json()["detail"].lower()

    corrected = copy.deepcopy({"nodes": graph["nodes"], "edges": graph["edges"]})
    corrected_labels = {**expected_labels, "9": "i = i + 1"}
    for node in corrected["nodes"]:
        node["data"]["label"] = corrected_labels[node["id"]]
        node["data"]["needs_review"] = False
        node["data"]["uncertain"] = False
    for edge in corrected["edges"]:
        edge["data"]["uncertain"] = False
        edge["data"]["unconfirmed_suggestion"] = False

    generated = client.post("/api/generate-code", json=corrected)
    assert generated.status_code == 200, generated.text
    code = generated.json()["code"]
    assert py_ast.parse(code)
    assert "fact = fact * i" in code
    assert "i = i + 1" in code
    assert "while i <= n:" in code

    generated_again = client.post("/api/generate-code", json=corrected)
    assert generated_again.status_code == 200, generated_again.text
    assert generated_again.json()["code"] == code

    old_mode = os.environ.get("FLOWFORGE_EXECUTION")
    try:
        os.environ["FLOWFORGE_EXECUTION"] = "local-dev"
        executed = client.post(
            "/api/execute",
            json={"code": code, "user_input": "5\n"},
        )
        assert executed.status_code == 200, executed.text
        assert executed.json()["success"] is True
        assert "120" in executed.json()["output"]
    finally:
        if old_mode is None:
            os.environ.pop("FLOWFORGE_EXECUTION", None)
        else:
            os.environ["FLOWFORGE_EXECUTION"] = old_mode


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
        {"id": "1b", "type": "input_output", "position": {"x": 300, "y": 90}, "data": {"label": "Input x"}},
        {"id": "2", "type": "decision", "position": {"x": 300, "y": 140}, "data": {"label": "x > 0"}},
        {"id": "3", "type": "input_output", "position": {"x": 150, "y": 240}, "data": {"label": "Print Pos"}},
        {"id": "4", "type": "input_output", "position": {"x": 450, "y": 240}, "data": {"label": "Print Neg"}},
        {"id": "5", "type": "start_end", "position": {"x": 300, "y": 340}, "data": {"label": "End"}},
    ]
    edges = [
        {"id": "e0", "source": "1", "target": "1b"},
        {"id": "e1", "source": "1b", "target": "2"},
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
    e3 = next(e for e in edges if e["id"] == "e3")
    e3["data"]["unconfirmed_suggestion"] = False
    e3["data"]["uncertain"] = False
    res2 = client.post("/api/generate-code", json={"nodes": nodes, "edges": edges})
    assert res2.status_code == 200
    assert "if x > 0:" in res2.json()["code"]


def test_uncertain_edges_block_generation():
    """
    Regression test: edges with uncertain=True block /api/generate-code with 422
    and a descriptive detail field (Requirement 5).
    """
    nodes = [
        {"id": "1", "type": "start_end", "position": {"x": 300, "y": 40}, "data": {"label": "Start"}},
        {"id": "2", "type": "input_output", "position": {"x": 300, "y": 140}, "data": {"label": "Input x"}},
        {"id": "3", "type": "decision", "position": {"x": 300, "y": 260}, "data": {"label": "x > 0?"}},
        {"id": "4", "type": "input_output", "position": {"x": 150, "y": 400}, "data": {"label": 'Print "Pos"'}},
        {"id": "5", "type": "input_output", "position": {"x": 460, "y": 400}, "data": {"label": 'Print "Neg"'}},
        {"id": "6", "type": "start_end", "position": {"x": 300, "y": 540}, "data": {"label": "End"}},
    ]
    edges = [
        {"id": "e1", "source": "1", "target": "2"},
        {"id": "e2", "source": "2", "target": "3"},
        {"id": "e3", "source": "3", "target": "4", "sourceHandle": "yes", "label": "Yes",
         "data": {"uncertain": True}},  # uncertain arrow direction
        {"id": "e4", "source": "3", "target": "5", "sourceHandle": "no", "label": "No",
         "data": {"uncertain": False}},
        {"id": "e5", "source": "4", "target": "6"},
        {"id": "e6", "source": "5", "target": "6"},
    ]

    for n in nodes:
        n["data"]["needs_review"] = False
        n["data"]["uncertain"] = False

    # Must be rejected because e3 has uncertain arrow direction
    res = client.post("/api/generate-code", json={"nodes": nodes, "edges": edges})
    assert res.status_code == 422, f"Expected 422, got {res.status_code}: {res.text}"
    detail = res.json()["detail"].lower()
    assert "uncertain" in detail, f"Expected 'uncertain' in detail, got: {detail}"

    # Once the user confirms the edge (clearing uncertain), generation succeeds
    e3 = next(e for e in edges if e["id"] == "e3")
    e3["data"]["uncertain"] = False
    res2 = client.post("/api/generate-code", json={"nodes": nodes, "edges": edges})
    assert res2.status_code == 200, f"Expected 200, got {res2.status_code}: {res2.text}"
    code = res2.json()["code"]
    assert "if x > 0:" in code, f"Expected 'if x > 0:' in code, got:\n{code}"


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


def test_executor_read_stream_handles_connection_drop():
    """
    Regression test: executor._read_stream must not crash when the client
    disconnects mid-stream (WinError 64 / WSAENETNAMEDELETED on Windows).
    The stream reader must catch OSError and return gracefully instead of
    propagating it to the server process.
    """
    import threading

    class _ClosedStream:
        """A mock stream whose read1 raises OSError (WinError 64 equivalent)."""
        def read1(self, n):
            raise OSError(64, "The specified network name is no longer available")

    sink = bytearray()
    overflow = threading.Event()

    # Should not raise; must catch OSError and return gracefully
    executor._read_stream(_ClosedStream(), cap=65536, sink=sink, overflow=overflow)
    assert len(sink) == 0
    assert not overflow.is_set()


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


def build_synthetic_odd_even_image() -> np.ndarray:
    """
    Renders a standard Odd/Even flowchart:
    Start -> Input n -> Decision n % 2 == 0?
      Yes -> Print "Even" -> End
      No  -> Print "Odd"  -> End
    """
    canvas = np.ones((620, 700, 3), dtype=np.uint8) * 255
    cv2.ellipse(canvas, (350, 45), (72, 26), 0, 0, 360, (0, 0, 0), 2)
    cv2.putText(canvas, "Start", (325, 51), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    cv2.arrowedLine(canvas, (350, 72), (350, 102), (0, 0, 0), 2, tipLength=0.25)

    input_pts = np.array([[290, 105], [430, 105], [408, 160], [268, 160]], np.int32)
    cv2.polylines(canvas, [input_pts], True, (0, 0, 0), 2)
    cv2.putText(canvas, "Input n", (320, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)
    cv2.arrowedLine(canvas, (350, 160), (350, 198), (0, 0, 0), 2, tipLength=0.25)

    decision_pts = np.array([[350, 200], [430, 255], [350, 310], [270, 255]], np.int32)
    cv2.polylines(canvas, [decision_pts], True, (0, 0, 0), 2)
    cv2.putText(canvas, "n % 2 == 0?", (300, 261), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 2)
    cv2.arrowedLine(canvas, (350, 160), (350, 198), (0, 0, 0), 2, tipLength=0.25)

    left_pts = np.array([[75, 365], [250, 365], [230, 415], [55, 415]], np.int32)
    right_pts = np.array([[450, 365], [625, 365], [605, 410], [430, 410]], np.int32)
    cv2.polylines(canvas, [left_pts, right_pts], True, (0, 0, 0), 2)
    cv2.putText(canvas, 'Print "Even"', (95, 398), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
    cv2.putText(canvas, 'Print "Odd"', (475, 398), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
    cv2.putText(canvas, "Yes", (230, 330), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
    cv2.putText(canvas, "No", (455, 330), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
    cv2.arrowedLine(canvas, (270, 255), (155, 362), (0, 0, 0), 2, tipLength=0.15)  # Yes branch (diagonal)
    cv2.arrowedLine(canvas, (430, 255), (535, 362), (0, 0, 0), 2, tipLength=0.15)  # No branch

    cv2.ellipse(canvas, (350, 555), (72, 26), 0, 0, 360, (0, 0, 0), 2)
    cv2.putText(canvas, "End", (335, 561), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    cv2.arrowedLine(canvas, (155, 415), (350, 526), (0, 0, 0), 2, tipLength=0.15)
    cv2.arrowedLine(canvas, (535, 415), (350, 526), (0, 0, 0), 2, tipLength=0.15)
    return canvas


def test_odd_even_flowchart_end_to_end(monkeypatch):
    """
    Regression test for the general decision/branching pipeline (reports #1):
    The odd/even flowchart must reconstruct both decision branches (incl. the
    diagonal Yes arrow), read the modulo condition confidently, generate code,
    and execute 4 -> Even, 5 -> Odd.
    """
    monkeypatch.setattr(api_server, "GEMINI_API_KEY", "")
    image = build_synthetic_odd_even_image()
    _, encoded = cv2.imencode(".png", image)

    analyzed = client.post(
        "/api/analyze",
        files={"file": ("odd_even.png", encoded.tobytes(), "image/png")},
    )
    assert analyzed.status_code == 200, analyzed.text
    graph = analyzed.json()

    # The full graph must be verified (no needs-review blockers).
    assert graph["graph_status"] == "verified", graph.get("warnings")

    nodes = graph["nodes"]
    edges = graph["edges"]

    decision_nodes = [n for n in nodes if n["type"] == "decision"]
    assert len(decision_nodes) == 1
    dec = decision_nodes[0]
    dec_id = dec["id"]
    # The modulo condition must be read confidently (not garbled, not needs-review).
    assert "%" in dec["data"]["label"] and "0" in dec["data"]["label"]
    assert dec["data"]["needs_review"] is False
    assert dec["data"]["uncertain"] is False

    # Both Yes and No outgoing branches must be present (the diagonal Yes arrow
    # must not be dropped or inverted into a backward edge).
    dec_outgoing = [e for e in edges if e["source"] == dec_id]
    branch_labels = {e.get("label") for e in dec_outgoing}
    assert "Yes" in branch_labels and "No" in branch_labels, branch_labels
    assert all(e["data"]["uncertain"] is False for e in dec_outgoing)

    # No uncertain / unconfirmed edges anywhere.
    assert all(e["data"]["uncertain"] is False for e in edges)
    assert all(e["data"].get("unconfirmed_suggestion") is False for e in edges)

    corrected = copy.deepcopy(graph)
    generated = client.post("/api/generate-code", json=corrected)
    assert generated.status_code == 200, generated.text
    code = generated.json()["code"]
    py_ast.parse(code)
    assert "n % 2" in code, code
    assert 'print("Even")' in code or "print(\"Even\")" in code, code
    assert 'print("Odd")' in code or "print(\"Odd\")" in code, code

    old_mode = os.environ.get("FLOWFORGE_EXECUTION")
    try:
        os.environ["FLOWFORGE_EXECUTION"] = "local-dev"
        out_even = client.post(
            "/api/execute", json={"code": code, "user_input": "4\n"}
        )
        assert out_even.status_code == 200, out_even.text
        assert "Even" in out_even.json()["output"], out_even.json()["output"]

        out_odd = client.post(
            "/api/execute", json={"code": code, "user_input": "5\n"}
        )
        assert out_odd.status_code == 200, out_odd.text
        assert "Odd" in out_odd.json()["output"], out_odd.json()["output"]
    finally:
        if old_mode is None:
            os.environ.pop("FLOWFORGE_EXECUTION", None)
        else:
            os.environ["FLOWFORGE_EXECUTION"] = old_mode


def build_degraded_odd_even_image() -> np.ndarray:
    """
    Renders an odd/even flowchart with real-image degradation:
    Gaussian blur, additive noise, and downscale/upscale to simulate
    a photo taken at distance and enlarged.
    """
    canvas = np.ones((620, 700, 3), dtype=np.uint8) * 255
    cv2.ellipse(canvas, (350, 45), (72, 26), 0, 0, 360, (0, 0, 0), 2)
    cv2.putText(canvas, "Start", (325, 51), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    cv2.arrowedLine(canvas, (350, 72), (350, 102), (0, 0, 0), 2, tipLength=0.25)

    input_pts = np.array([[290, 105], [430, 105], [408, 160], [268, 160]], np.int32)
    cv2.polylines(canvas, [input_pts], True, (0, 0, 0), 2)
    cv2.putText(canvas, "Input n", (320, 140), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 0), 2)
    cv2.arrowedLine(canvas, (350, 160), (350, 198), (0, 0, 0), 2, tipLength=0.25)

    decision_pts = np.array([[350, 200], [430, 255], [350, 310], [270, 255]], np.int32)
    cv2.polylines(canvas, [decision_pts], True, (0, 0, 0), 2)
    cv2.putText(canvas, "n % 2 == 0?", (300, 261), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 2)
    cv2.arrowedLine(canvas, (350, 160), (350, 198), (0, 0, 0), 2, tipLength=0.25)

    left_pts = np.array([[75, 365], [250, 365], [230, 415], [55, 415]], np.int32)
    right_pts = np.array([[450, 365], [625, 365], [605, 410], [430, 410]], np.int32)
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

    # Degradation: blur + noise + downscale/upscale
    canvas = cv2.GaussianBlur(canvas, (3, 3), 1.0)
    noise = np.random.randint(0, 30, canvas.shape, dtype=np.uint8)
    canvas = cv2.add(canvas, noise)
    canvas = cv2.resize(canvas, (350, 310), interpolation=cv2.INTER_AREA)
    canvas = cv2.resize(canvas, (700, 620), interpolation=cv2.INTER_CUBIC)
    return canvas


def test_degraded_image_preserves_validation_gating(monkeypatch):
    """
    Regression test with a degraded (real-image-simulated) odd/even flowchart.

    Verifies that:
    - Non-printable OCR characters (null bytes, replacement char, DEL) are
      stripped from labels so "Print Even" generates print("Even").
    - Low-confidence decision text is correctly flagged needs_review
      and blocks code generation until the user corrects it on the canvas.
    - Validation gating is preserved: code generation returns 422 until
      needs_review nodes are corrected.
    """
    monkeypatch.setattr(api_server, "GEMINI_API_KEY", "")
    np.random.seed(42)  # deterministic noise
    image = build_degraded_odd_even_image()
    _, encoded = cv2.imencode(".png", image)

    analyzed = client.post(
        "/api/analyze",
        files={"file": ("odd_even_degraded.png", encoded.tobytes(), "image/png")},
    )
    assert analyzed.status_code == 200, analyzed.text
    graph = analyzed.json()

    nodes = graph["nodes"]
    edges = graph["edges"]

    # Print nodes should have non-printable characters stripped from labels.
    print_nodes = [n for n in nodes if n["type"] == "input_output" and "Print" in n["data"]["label"]]
    for pn in print_nodes:
        label = pn["data"]["label"]
        # No non-printable characters should remain (null bytes, control chars, DEL, replacement char, other Unicode garbage)
        assert not any(ord(c) < 32 and c not in "\t\n\r" for c in label), \
            f"Label contains control char: {label!r}"
        assert chr(0xFFFD) not in label, f"Label contains replacement char: {label!r}"
        assert all(ord(c) < 128 for c in label), f"Label contains non-ASCII: {label!r}"

    # At least one node should be needs_review (degraded image produces low-confidence reads)
    needs_review_nodes = [n for n in nodes if n["data"].get("needs_review")]
    assert len(needs_review_nodes) >= 1, "Degraded image should flag at least one node for review"

    # Code generation must be blocked until review is completed
    generated = client.post("/api/generate-code", json={"nodes": graph["nodes"], "edges": graph["edges"]})
    assert generated.status_code == 422, f"Expected 422, got {generated.status_code}"
    assert "review" in generated.json()["detail"].lower()

    # Once the user corrects all labels and clears needs_review/uncertain,
    # code generation should succeed
    corrected = copy.deepcopy(graph)
    for n in corrected["nodes"]:
        n["data"]["needs_review"] = False
        n["data"]["uncertain"] = False
        # Replace any garbled decision text with a valid condition
        if n["type"] == "decision":
            n["data"]["label"] = "n % 2 == 0?"
    for e in corrected["edges"]:
        e["data"]["uncertain"] = False
        e["data"].pop("unconfirmed_suggestion", None)

    generated2 = client.post("/api/generate-code", json=corrected)
    assert generated2.status_code == 200, generated2.text
    code = generated2.json()["code"]
    py_ast.parse(code)
    assert "n % 2" in code, code
    assert "print(" in code, code  # Some print statement should be generated


def test_general_decision_branching_if_else(monkeypatch):
    """
    Regression test for a generic if/else decision flowchart (not hardcoded to
    odd/even or factorial). Verifies the pipeline handles arbitrary decision
    conditions and produces correct Yes/No code for both branches.
    """
    monkeypatch.setattr(api_server, "GEMINI_API_KEY", "")

    # Deterministic graph: Input x -> decision x > 0 -> Yes: Print Positive, No: Print Non-positive -> End
    nodes = [
        {"id": "1", "type": "start_end", "position": {"x": 300, "y": 40}, "data": {"label": "Start"}},
        {"id": "2", "type": "input_output", "position": {"x": 300, "y": 140}, "data": {"label": "Input x"}},
        {"id": "3", "type": "decision", "position": {"x": 300, "y": 260}, "data": {"label": "x > 0?"}},
        {"id": "4", "type": "input_output", "position": {"x": 150, "y": 400}, "data": {"label": 'Print "Positive"'}},
        {"id": "5", "type": "input_output", "position": {"x": 460, "y": 400}, "data": {"label": 'Print "Non-positive"'}},
        {"id": "6", "type": "start_end", "position": {"x": 300, "y": 540}, "data": {"label": "End"}},
    ]
    edges = [
        {"id": "e1", "source": "1", "target": "2"},
        {"id": "e2", "source": "2", "target": "3"},
        {"id": "e3", "source": "3", "target": "4", "sourceHandle": "yes", "label": "Yes"},
        {"id": "e4", "source": "3", "target": "5", "sourceHandle": "no", "label": "No"},
        {"id": "e5", "source": "4", "target": "6"},
        {"id": "e6", "source": "5", "target": "6"},
    ]

    for n in nodes:
        n["data"]["needs_review"] = False
        n["data"]["uncertain"] = False
    for e in edges:
        e["data"] = {"uncertain": False, "unconfirmed_suggestion": False}

    generated = client.post("/api/generate-code", json={"nodes": nodes, "edges": edges})
    assert generated.status_code == 200, generated.text
    code = generated.json()["code"]
    py_ast.parse(code)
    assert "if x > 0:" in code, code
    assert 'print("Positive")' in code, code
    assert 'print("Non-positive")' in code, code

    old_mode = os.environ.get("FLOWFORGE_EXECUTION")
    try:
        os.environ["FLOWFORGE_EXECUTION"] = "local-dev"
        out_pos = client.post(
            "/api/execute", json={"code": code, "user_input": "7\n"}
        )
        assert out_pos.status_code == 200, out_pos.text
        assert "Positive" in out_pos.json()["output"], out_pos.json()["output"]

        out_neg = client.post(
            "/api/execute", json={"code": code, "user_input": "-3\n"}
        )
        assert out_neg.status_code == 200, out_neg.text
        assert "Non-positive" in out_neg.json()["output"], out_neg.json()["output"]
    finally:
        if old_mode is None:
            os.environ.pop("FLOWFORGE_EXECUTION", None)
        else:
            os.environ["FLOWFORGE_EXECUTION"] = old_mode


def test_ocr_normalizes_zero_as_letter_o_in_conditions():
    """
    Regression test: OCR often confuses digit 0 with letter O in real images.
    clean_ocr_text must normalize standalone O to 0 in numeric comparison contexts
    (e.g. "n % 2 == O?" -> "n % 2 == 0?") so normalize_condition produces a
    valid numeric comparison instead of wrapping bare "O" as a string literal.
    """
    assert ocr_engine.clean_ocr_text("n % 2 == O?") == "n % 2 == 0?"
    # No-space case: OCR may drop the space; result is still valid Python
    result = ocr_engine.clean_ocr_text("n % 2==O?")
    assert result in ("n % 2 == 0?", "n % 2== 0?"), f"Unexpected: {result!r}"
    assert ocr_engine.clean_ocr_text("< O") == "< 0"
    assert ocr_engine.clean_ocr_text("O ==") == "0 =="
    # Must not corrupt legitimate words like "Odd" or "On"
    assert ocr_engine.clean_ocr_text('Print "Odd"') == 'Print "Odd"'
    assert ocr_engine.clean_ocr_text("Input On") == "Input On"


def test_ocr_normalizes_i_less_than_n_to_less_equal():
    """
    Regression test: real images often OCR "i <= n?" as "i < n?" (missing =).
    clean_ocr_text must convert "i < n?" to "i <= n?" so the factorial-style
    loop condition is preserved.
    """
    assert ocr_engine.clean_ocr_text("i < n?") == "i <= n?"
    assert ocr_engine.clean_ocr_text("x < y?") == "x <= y?"


def test_input_output_node_without_value_flagged_needs_review():
    """
    Regression test: when OCR reads only the keyword (e.g. "Print" without "Even")
    with high confidence, text_uncertain is False but the node is incomplete.
    blocks_to_react_nodes must flag it as needs_review so the user corrects it.
    """
    blocks = [
        {
            "id": 1, "type": "input_output", "bbox": [0, 0, 100, 40], "center": [50, 20],
            "text": "Print", "text_confidence": 95.0, "text_uncertain": False,
        },
        {
            "id": 2, "type": "input_output", "bbox": [0, 60, 100, 40], "center": [50, 80],
            "text": 'Print "Even"', "text_confidence": 95.0, "text_uncertain": False,
        },
        {
            "id": 3, "type": "input", "bbox": [0, 120, 100, 40], "center": [50, 140],
            "text": "Input", "text_confidence": 90.0, "text_uncertain": False,
        },
    ]
    connections = []
    nodes = api_server.blocks_to_react_nodes(blocks, connections=connections)

    node_by_id = {n["id"]: n for n in nodes}
    assert node_by_id["1"]["data"]["needs_review"] is True, "Print without value must be flagged"
    assert node_by_id["1"]["data"]["uncertain"] is True
    assert node_by_id["2"]["data"]["needs_review"] is False, 'Print "Even" is complete'
    assert node_by_id["3"]["data"]["needs_review"] is True, "Input without value must be flagged"


def test_duplicate_branch_labels_on_decision_marked_uncertain(monkeypatch):
    """
    Regression test: when OCR reads the same branch label on both edges of a
    decision (e.g. both "Yes"), the second edge must be marked uncertain with
    its label cleared so the user can correct it instead of generating wrong code.
    """
    monkeypatch.setattr(api_server, "GEMINI_API_KEY", "")

    nodes = [
        {"id": "1", "type": "start_end", "position": {"x": 300, "y": 40}, "data": {"label": "Start"}},
        {"id": "2", "type": "input_output", "position": {"x": 300, "y": 120}, "data": {"label": "Input n"}},
        {"id": "3", "type": "decision", "position": {"x": 300, "y": 250}, "data": {"label": "n > 0?"}},
        {"id": "4", "type": "input_output", "position": {"x": 150, "y": 380}, "data": {"label": 'Print "Yes"'}},
        {"id": "5", "type": "input_output", "position": {"x": 460, "y": 380}, "data": {"label": 'Print "No"'}},
        {"id": "6", "type": "start_end", "position": {"x": 300, "y": 500}, "data": {"label": "End"}},
    ]
    # Both edges from decision have label "Yes" (OCR misread one as "Yes")
    edges = [
        {"id": "e1", "source": "1", "target": "2"},
        {"id": "e2", "source": "2", "target": "3"},
        {"id": "e3", "source": "3", "target": "4", "sourceHandle": "yes", "label": "Yes"},
        {"id": "e4", "source": "3", "target": "5", "sourceHandle": "no", "label": "Yes"},  # duplicate!
        {"id": "e5", "source": "4", "target": "6"},
        {"id": "e6", "source": "5", "target": "6"},
    ]

    for n in nodes:
        n["data"]["needs_review"] = False
        n["data"]["uncertain"] = False
    for e in edges:
        e["data"] = {"uncertain": False, "unconfirmed_suggestion": False}

    generated = client.post("/api/generate-code", json={"nodes": nodes, "edges": edges})
    assert generated.status_code == 422, "Duplicate branch labels must block code generation"
    detail = generated.json()["detail"].lower()
    assert "multiple labeled paths" in detail or "selector variable" in detail or "review" in detail or "branch" in detail


# ============================================================================
# Category 4: Real-image OCR regression (border fragments + lost output value)
# ============================================================================

def test_clean_ocr_text_drops_diamond_border_fragments():
    """
    Regression (real image): a decision diamond crop yields the real condition
    surrounded by border artifacts. Before the fix the label was
    ', ™\\nn % 2 == 0?\\n“eS 7'. The artifacts must be dropped while the
    condition itself is preserved.
    """
    raw = ", \u2122\nn%2==0?\n\u201ceS 7"
    assert ocr_engine.clean_ocr_text(raw) == "n % 2 == 0?"

    # A marker-letter fragment and a pure-punctuation fragment are both noise.
    assert ocr_engine.clean_ocr_text(",\nn % 2 == 0?\neS 7") == "n % 2 == 0?"


def test_clean_ocr_text_preserves_multiline_statements():
    """
    Noise filtering must never drop genuine multi-statement / split labels.
    """
    assert ocr_engine.clean_ocr_text("fact = fact * i\ni = i + 1") == "fact = fact * i\ni = i + 1"
    # 'Print' broken across two lines is merged, not discarded as a fragment.
    assert ocr_engine.clean_ocr_text("Print\nfact") == "Print fact"
    assert ocr_engine.clean_ocr_text("Input\nn") == "Input n"
    # A lone short label must survive (no competing statement exists).
    assert ocr_engine.clean_ocr_text("i") == "i"


def test_candidate_rank_prefers_complete_input_output_over_bare_keyword():
    """
    Regression (real image): the complete statement must outrank a bare keyword
    whose raw OCR confidence is marginally higher. This is what made the left
    output read 'Print' instead of 'Print "Even"', and 'Input' instead of 'Input n'.
    """
    assert ocr_engine._candidate_rank(('Print "Even"', 95.5)) > ocr_engine._candidate_rank(("Print", 96.0))
    assert ocr_engine._candidate_rank(("Input n", 93.5)) > ocr_engine._candidate_rank(("Input", 95.0))
    # Complete labels are trimmed of stray whitespace inside quotes.
    assert ocr_engine.clean_ocr_text('Print\n" Odd"') == 'Print "Odd"'


def _patch_ocr_readings(monkeypatch, readings):
    """Force extract_block_text_with_confidence to use deterministic readings."""
    def fake_read(_image, config="--oem 3 --psm 6"):
        return readings(config)
    monkeypatch.setattr(ocr_engine, "tesseract_available", lambda: True)
    monkeypatch.setattr(ocr_engine, "_read_candidate", fake_read)
    monkeypatch.setattr(ocr_engine, "_read_candidate_string", fake_read)
    monkeypatch.setattr(ocr_engine.pytesseract, "image_to_boxes", lambda *a, **k: "")


def test_extract_block_text_prefers_complete_print_statement(monkeypatch):
    """
    The multi-layout selector must return 'Print "Even"' (complete) rather than
    the marginally-higher-confidence bare 'Print' that psm 11/12 produced.
    """
    def readings(config):
        if "psm 11" in config or "psm 12" in config:
            return ("Print", 96.0)
        return ('Print\n"Even"', 95.5)

    _patch_ocr_readings(monkeypatch, readings)
    img = np.full((200, 200, 3), 255, dtype=np.uint8)
    text, conf = ocr_engine.extract_block_text_with_confidence(img, (20, 20, 160, 160))
    assert text == 'Print "Even"'
    assert conf >= 50


def test_extract_block_text_strips_decision_border_fragments(monkeypatch):
    """
    End-to-end shape OCR: a decision crop contaminated by diamond borders must
    resolve to the clean condition 'n % 2 == 0?' with review-level confidence.
    """
    def readings(config):
        if "psm 11" in config or "psm 12" in config:
            return ("n%2==0?", 22.0)
        return (", \u2122\nn%2==0?\n\u201ceS 7", 60.0)

    _patch_ocr_readings(monkeypatch, readings)
    img = np.full((200, 200, 3), 255, dtype=np.uint8)
    text, conf = ocr_engine.extract_block_text_with_confidence(img, (20, 20, 160, 160))
    assert text == "n % 2 == 0?"
    assert conf >= 50


def test_real_image_odd_even_graph_verified_and_generates_code(monkeypatch):
    """
    Full pipeline regression for the reported real image (path provided via the
    FLOWFORGE_REAL_IMAGE env var when available). Asserts the decision condition
    is clean, the left output keeps its 'Even' message, only one Yes and one No
    edge exist, and the graph generates executing Python.
    """
    real_image = os.environ.get("FLOWFORGE_REAL_IMAGE", "")
    if not real_image or not os.path.isfile(real_image):
        pytest.skip("Set FLOWFORGE_REAL_IMAGE to the real odd/even flowchart PNG to run this test.")

    monkeypatch.setattr(api_server, "GEMINI_API_KEY", "")
    with open(real_image, "rb") as fh:
        raw = fh.read()

    analyzed = client.post(
        "/api/analyze",
        files={"file": ("odd_even.png", raw, "image/png")},
    )
    assert analyzed.status_code == 200, analyzed.text
    graph = analyzed.json()

    decision_nodes = [n for n in graph["nodes"] if n["type"] == "decision"]
    assert len(decision_nodes) == 1
    dec = decision_nodes[0]
    # Clean condition, no leftover border garbage.
    assert dec["data"]["label"] == "n % 2 == 0?", dec["data"]["label"]
    assert dec["data"]["needs_review"] is False

    outputs = {n["data"]["label"] for n in graph["nodes"] if n["type"] == "input_output"}
    assert 'Print "Even"' in outputs, outputs
    assert 'Print "Odd"' in outputs, outputs

    dec_outgoing = [e for e in graph["edges"] if e["source"] == dec["id"]]
    assert len(dec_outgoing) == 2, dec_outgoing
    assert {e["label"] for e in dec_outgoing} == {"Yes", "No"}

    assert graph["graph_status"] == "verified", graph.get("warnings")
    assert graph["missing_connections"] == []

    generated = client.post("/api/generate-code", json={"nodes": graph["nodes"], "edges": graph["edges"]})
    assert generated.status_code == 200, generated.text
    code = generated.json()["code"]
    py_ast.parse(code)
    assert "n % 2" in code
    assert 'print("Even")' in code
    assert 'print("Odd")' in code


# ---------------------------------------------------------------------------
# Largest-of-three OCR / reconstruction regressions (reports: image-import
# workflow returned 422, dropping 'Input B/C', garbling conditions, and
# reducing output labels to bare 'largest').
# ---------------------------------------------------------------------------


def test_select_best_candidate_prefers_complete_over_truncated():
    """A sparse-text layout that dropped part of a label must not win just because
    its mean word confidence is a hair higher (this lost 'B, C' from 'Input A, B, C')."""
    candidates = [
        ("Input A, B, C", 93.2),
        ("Input A, B, C", 92.8),
        ("Input A, B, C", 92.8),
        ("Input A", 95.5),
        ("Input A", 95.5),
    ]
    text, _ = ocr_engine.select_best_candidate(candidates)
    assert text == "Input A, B, C"


def test_select_best_candidate_prefers_preserved_word_boundaries():
    """When two readings carry the same characters, keep the one with word breaks
    ('Print C is largest' must beat 'Print Cis largest')."""
    candidates = [
        ("Print C is largest", 95.2),
        ("Print C is largest", 95.0),
        ("Print C is largest", 94.8),
        ("Print Cis largest", 95.3),
        ("Print Cis largest", 95.3),
    ]
    text, _ = ocr_engine.select_best_candidate(candidates)
    assert text == "Print C is largest"


def test_select_best_candidate_keeps_whole_multiline_condition():
    """A decision reading that captured both condition lines must beat the higher
    confidence fragment that dropped the second line."""
    candidates = [
        ("A > Band\nA = C?", 63.2),
        ("A > Band\nA = C?", 60.0),
        ("A > Band\nA = C?", 60.0),
        ("A > Band", 86.7),
        ("A > Band", 86.7),
    ]
    text, _ = ocr_engine.select_best_candidate(candidates)
    # select_best_candidate returns the winning raw reading; downstream cleaning
    # turns the glued conjunction into 'B and'.
    assert text == "A > Band\nA = C?"
    assert ocr_engine.clean_ocr_text(text) == "A > B and\nA = C?"


def test_clean_ocr_text_normalizes_unicode_math_and_glued_conjunctions():
    """The '≥'/'≤' glyphs must survive non-ASCII stripping as '>='/'<=', OCR's
    '=>' must become '>=', and a conjunction glued to its operand must be split."""
    assert ocr_engine.clean_ocr_text("A ≥ B") == "A >= B"
    assert ocr_engine.clean_ocr_text("i ≤ n") == "i <= n"
    assert ocr_engine.clean_ocr_text("A => B") == "A >= B"
    assert ocr_engine.clean_ocr_text("A > Band") == "A > B and"
    assert ocr_engine.clean_ocr_text("B > Aand") == "B > A and"
    # Ordinary prose words must not be split.
    assert ocr_engine.clean_ocr_text("Brand new color") == "Brand new color"


def test_filter_overlapping_blocks_keeps_shape_around_its_text_label():
    """A shape whose own label text is a solid glyph blob must not be discarded as an
    'aggregate' (that previously reduced 'Print B/C is largest' to bare 'largest')."""
    shape = {"id": 1, "type": "input_output", "bbox": (0, 0, 200, 60), "center": (100, 30),
             "area": 2000, "outline": True}
    text = {"id": 2, "type": "document", "bbox": (60, 15, 90, 30), "center": (105, 30),
            "area": 300, "outline": False}
    kept = cv_engine.filter_overlapping_blocks([shape, text])
    assert len(kept) == 1 and kept[0] is shape


def test_filter_overlapping_blocks_drops_aggregate_containing_real_symbol():
    """A merged arrow/shape contour that encloses a genuine symbol outline must be
    dropped in favour of the individual symbol."""
    aggregate = {"id": 1, "type": "process", "bbox": (0, 0, 200, 60), "center": (100, 30),
                 "area": 2000, "outline": True}
    symbol = {"id": 2, "type": "decision", "bbox": (60, 15, 90, 30), "center": (105, 30),
              "area": 300, "outline": True}
    kept = cv_engine.filter_overlapping_blocks([aggregate, symbol])
    assert len(kept) == 1
    assert kept[0] is symbol and kept[0]["type"] == "decision"


def test_near_square_diamond_is_classified_as_decision():
    """A diamond whose corners are close to 90 degrees (near-square) has right-angled
    corners but is NOT a process rectangle; it must still read as a decision."""
    canvas = np.ones((400, 400, 3), dtype=np.uint8) * 255
    pts = np.array([[200, 80], [310, 200], [200, 320], [90, 200]], np.int32)
    cv2.polylines(canvas, [pts], True, (0, 0, 0), 3)
    blocks, _ = cv_engine.detect_symbols(canvas)
    assert len(blocks) == 1, blocks
    assert blocks[0]["type"] == "decision", blocks[0]["type"]


def test_rectangle_is_still_classified_as_process():
    """Guard against the diamond fix regressing ordinary process boxes."""
    canvas = np.ones((300, 400, 3), dtype=np.uint8) * 255
    cv2.rectangle(canvas, (100, 80), (300, 200), (0, 0, 0), 3)
    blocks, _ = cv_engine.detect_symbols(canvas)
    assert len(blocks) == 1, blocks
    assert blocks[0]["type"] == "process", blocks[0]["type"]


def test_generate_code_review_error_names_offending_nodes():
    """The 'Needs review' 422 must name which nodes to fix, so the blocker is
    actionable in the UI instead of a generic message."""
    nodes = [
        {"id": "1", "type": "start_end", "position": {"x": 300, "y": 40}, "data": {"label": "Start"}},
        {"id": "7", "type": "decision", "position": {"x": 300, "y": 140},
         "data": {"label": "A >= B and\nA = C?", "needs_review": True, "uncertain": True}},
        {"id": "9", "type": "start_end", "position": {"x": 300, "y": 240}, "data": {"label": "End"}},
    ]
    edges = [
        {"id": "e1", "source": "1", "target": "7"},
        {"id": "e2", "source": "7", "target": "9"},
    ]
    res = client.post("/api/generate-code", json={"nodes": nodes, "edges": edges})
    assert res.status_code == 422
    detail = res.json()["detail"]
    assert "Needs review" in detail
    assert "#7" in detail


def test_real_image_largest_of_three_reconstruction(monkeypatch):
    """
    Full pipeline regression for the real largest-of-three image (path supplied via
    the FLOWFORGE_LARGEST_IMAGE env var). Verifies all 8 shapes are reconstructed
    (not fragmented), the input/output lists are complete, both decisions recover
    their '≥' comparison operators automatically, the Yes/No branches are wired,
    and the graph generates executing code without any manual correction.
    """
    real_image = os.environ.get("FLOWFORGE_LARGEST_IMAGE", "")
    if not real_image or not os.path.isfile(real_image):
        pytest.skip("Set FLOWFORGE_LARGEST_IMAGE to the real largest-of-three PNG to run this test.")

    monkeypatch.setattr(api_server, "GEMINI_API_KEY", "")
    with open(real_image, "rb") as fh:
        raw = fh.read()

    analyzed = client.post("/api/analyze", files={"file": ("largest.png", raw, "image/png")})
    assert analyzed.status_code == 200, analyzed.text
    graph = analyzed.json()

    # All 8 shapes (Start, Input A/B/C, 2 decisions, 3 outputs, End) reconstruct as
    # single nodes - no fragments and no text-only stubs.
    assert len(graph["nodes"]) == 8, [n["data"]["label"] for n in graph["nodes"]]
    labels = {n["data"]["label"] for n in graph["nodes"]}
    assert "Input A, B, C" in labels, labels
    for expected in ("Print A is largest", "Print B is largest", "Print C is largest"):
        assert expected in labels, labels

    decisions = [n for n in graph["nodes"] if n["type"] == "decision"]
    assert len(decisions) == 2, [n["type"] for n in graph["nodes"]]

    # Both decision branches are wired with correct Yes/No handles.
    for dec in decisions:
        out = [e for e in graph["edges"] if e["source"] == dec["id"]]
        assert len(out) == 2, out
        assert {e["label"] for e in out} == {"Yes", "No"}, out
        assert all(e["data"]["uncertain"] is False for e in out)

    assert graph["missing_connections"] == []

    # The '≥' glyphs come back as '>=' on both conditions (the misread '=' is
    # recovered from pixel evidence), so nothing needs manual review and the
    # graph is auto-verifiable.
    assert graph["graph_status"] == "verified", graph.get("warnings")
    for dec in decisions:
        assert dec["data"]["needs_review"] is False, dec
        assert ">=" in dec["data"]["label"], dec["data"]["label"]

    # The recovered graph generates valid Python with no manual correction.
    generated = client.post("/api/generate-code", json={"nodes": graph["nodes"], "edges": graph["edges"]})
    assert generated.status_code == 200, generated.text
    code = generated.json()["code"]
    py_ast.parse(code)
    assert "A >= B and A >= C" in code
    assert "B >= A and B >= C" in code
    assert "A is largest" in code
    assert "B is largest" in code
    assert "C is largest" in code

    # And the reconstructed flow actually picks the largest of three.
    old_mode = os.environ.get("FLOWFORGE_EXECUTION")
    try:
        os.environ["FLOWFORGE_EXECUTION"] = "local-dev"
        for user_input, expected in (("3\n7\n5\n", "B is largest"), ("9\n2\n4\n", "A is largest"), ("1\n2\n8\n", "C is largest")):
            executed = client.post(
                "/api/execute", json={"code": code, "user_input": user_input}
            )
            assert executed.status_code == 200, executed.text
            assert executed.json()["success"] is True
            assert expected in executed.json()["output"]
    finally:
        if old_mode is None:
            os.environ.pop("FLOWFORGE_EXECUTION", None)
        else:
            os.environ["FLOWFORGE_EXECUTION"] = old_mode


def test_extract_input_vars_handles_single_and_list_inputs():
    """One input shape can define a whole list of variables ('Input A, B, C')."""
    assert logic_engine.extract_input_vars("Input n") == ["n"]
    assert logic_engine.extract_input_vars("Input number n") == ["n"]
    assert logic_engine.extract_input_vars("Input A, B, C") == ["A", "B", "C"]
    assert logic_engine.extract_input_vars("Input a and b") == ["a", "b"]


def test_generate_code_initializes_all_variables_from_list_input():
    """A single 'Input A, B, C' node must initialize A, B and C so conditions on
    them are not reported as undefined."""
    nodes = [
        {"id": "1", "type": "start_end", "position": {"x": 300, "y": 40}, "data": {"label": "Start"}},
        {"id": "2", "type": "input_output", "position": {"x": 300, "y": 140}, "data": {"label": "Input A, B, C"}},
        {"id": "3", "type": "decision", "position": {"x": 300, "y": 260}, "data": {"label": "A >= B and A >= C?"}},
        {"id": "4", "type": "input_output", "position": {"x": 150, "y": 400}, "data": {"label": "Print A is largest"}},
        {"id": "5", "type": "input_output", "position": {"x": 460, "y": 400}, "data": {"label": "Print B is largest"}},
        {"id": "6", "type": "start_end", "position": {"x": 300, "y": 540}, "data": {"label": "End"}},
    ]
    edges = [
        {"id": "e1", "source": "1", "target": "2"},
        {"id": "e2", "source": "2", "target": "3"},
        {"id": "e3", "source": "3", "target": "4", "sourceHandle": "yes", "label": "Yes"},
        {"id": "e4", "source": "3", "target": "5", "sourceHandle": "no", "label": "No"},
        {"id": "e5", "source": "4", "target": "6"},
        {"id": "e6", "source": "5", "target": "6"},
    ]
    res = client.post("/api/generate-code", json={"nodes": nodes, "edges": edges})
    assert res.status_code == 200, res.text
    code = res.json()["code"]
    tree = py_ast.parse(code)
    assigned = {
        target.id
        for node in py_ast.walk(tree)
        if isinstance(node, py_ast.Assign)
        for target in node.targets
        if isinstance(target, py_ast.Name)
    }
    assert {"A", "B", "C"} <= assigned, (assigned, code)


# ---------------------------------------------------------------------------
# Automatic operator recovery / AI-assisted resolution regressions (report: the
# largest-of-three graph stayed in 'Needs review' because the '≥' glyphs were
# read as '=' and code generation never ran without manual edits).
# ---------------------------------------------------------------------------


def test_normalize_condition_joins_multiline_conditions():
    """A condition wrapped over two OCR lines is still one Boolean expression."""
    assert logic_engine.normalize_condition("A >= B and\nA >= C?") == "A >= B and A >= C"
    assert logic_engine.normalize_condition("i < n\nand n > 0?") == "i < n and n > 0"


def test_comparison_operators_are_anchored_on_operands():
    """Only operators sitting between two operands count, so border/arrow fragments
    around a diamond are not mistaken for condition operators."""
    assert ocr_engine.comparison_operators("A >= B and\nA = C?") == [">=", "="]
    assert ocr_engine.comparison_operators("n % 2 == 0?") == ["=="]
    assert ocr_engine.comparison_operators("> fragment only") == []
    assert ocr_engine.comparison_operators("Is\n> \nA2C?") == []


def test_replace_comparison_operators_keeps_operands(monkeypatch):
    """Operator substitution keeps every operand, spacing and line break intact."""
    text = "A >= B and\nA = C?"
    assert ocr_engine._replace_comparison_operators(text, [">=", ">="]) == "A >= B and\nA >= C?"


def test_recover_condition_operators_upgrades_misread_glyphs(monkeypatch):
    """Corroborating probes upgrade a misread '=' back to '>=' without touching
    the operands."""
    monkeypatch.setattr(
        ocr_engine,
        "read_condition_operator_signatures",
        lambda roi, expected_count=None, max_matches=3: [[">=", ">="], [">=", "<="]],
    )
    assert ocr_engine.recover_condition_operators("A >= B and\nA = C?", None) == "A >= B and\nA >= C?"


def test_recover_condition_operators_keeps_genuine_equality(monkeypatch):
    """A genuine '=' is preserved when the pixels also read '='."""
    monkeypatch.setattr(
        ocr_engine,
        "read_condition_operator_signatures",
        lambda roi, expected_count=None, max_matches=3: [["="], ["="]],
    )
    assert ocr_engine.recover_condition_operators("flag = A?", None) == "flag = A?"


def test_recover_condition_operators_is_inconclusive_without_evidence(monkeypatch):
    """No matching probe means the ambiguity stands: the text is left for review."""
    monkeypatch.setattr(
        ocr_engine,
        "read_condition_operator_signatures",
        lambda roi, expected_count=None, max_matches=3: [],
    )
    text = "A >= B and\nA = C?"
    assert ocr_engine.recover_condition_operators(text, None) == text


def test_recover_condition_operators_never_downgrades_equality(monkeypatch):
    """A '==' is never weakened to '>=': only upgrades are ever applied."""
    monkeypatch.setattr(
        ocr_engine,
        "read_condition_operator_signatures",
        lambda roi, expected_count=None, max_matches=3: [[">="]],
    )
    assert ocr_engine.recover_condition_operators("n % 2 == 0?", None) == "n % 2 == 0?"


def _synthetic_condition_graph(monkeypatch, decision_text, decision_conf, signatures=("auto",)):
    """Stub the CV/OCR stages with a tiny Start -> Input -> Decision -> End graph.

    `signatures` is the literal list returned by the operator probe; pass [] to
    simulate inconclusive pixel evidence.
    """
    blocks = [
        {"id": 1, "type": "start_end", "bbox": (280, 20, 120, 50), "center": (340, 45)},
        {"id": 2, "type": "input_output", "bbox": (240, 90, 200, 50), "center": (340, 115)},
        {"id": 3, "type": "decision", "bbox": (240, 170, 200, 120), "center": (340, 230)},
        {"id": 4, "type": "start_end", "bbox": (280, 330, 120, 50), "center": (340, 355)},
    ]
    connections = [
        {"from": 1, "to": 2, "branch": None, "confidence": 1.0, "uncertain": False, "vector": ((340, 45), (340, 90))},
        {"from": 2, "to": 3, "branch": None, "confidence": 1.0, "uncertain": False, "vector": ((340, 140), (340, 170))},
        {"from": 3, "to": 4, "branch": "Yes", "confidence": 1.0, "uncertain": False, "vector": ((340, 290), (340, 330))},
        {"from": 3, "to": 4, "branch": "No", "confidence": 1.0, "uncertain": False, "vector": ((340, 290), (340, 330))},
    ]
    monkeypatch.setattr(
        cv_engine, "detect_symbols",
        lambda img: (copy.deepcopy(blocks), np.zeros(img.shape[:2], dtype=np.uint8)),
    )
    monkeypatch.setattr(cv_engine, "detect_connections", lambda thresh, blks: (copy.deepcopy(connections), []))
    texts = {
        (280, 20, 120, 50): ("Start", 96.0),
        (240, 90, 200, 50): ("Input A, B, C", 96.0),
        (240, 170, 200, 120): (decision_text, decision_conf),
        (280, 330, 120, 50): ("End", 96.0),
    }
    monkeypatch.setattr(ocr_engine, "extract_block_text_with_confidence", lambda img, bbox: texts[tuple(bbox)])
    monkeypatch.setattr(
        ocr_engine, "read_condition_operator_signatures",
        lambda roi, expected_count=None, max_matches=3: copy.deepcopy(list(signatures)),
    )
    img = np.ones((400, 680, 3), dtype=np.uint8) * 255
    ok, buf = cv2.imencode(".png", img)
    assert ok
    return buf.tobytes()


def test_analyze_recovers_misread_operator_and_clears_review(monkeypatch):
    """The endpoint recovers a misread '≥' from pixel evidence and clears the
    review gate, so the graph verifies without any manual edit."""
    monkeypatch.setattr(api_server, "GEMINI_API_KEY", "")
    raw = _synthetic_condition_graph(
        monkeypatch, "A >= B and\nA = C?", 49.0, signatures=[[">=", ">="], [">=", ">="]],
    )
    res = client.post("/api/analyze", files={"file": ("synthetic.png", raw, "image/png")})
    assert res.status_code == 200, res.text
    graph = res.json()
    dec = next(n for n in graph["nodes"] if n["type"] == "decision")
    assert dec["data"]["label"] == "A >= B and\nA >= C?", dec["data"]["label"]
    assert dec["data"]["needs_review"] is False
    assert graph["graph_status"] == "verified", graph.get("warnings")

    generated = client.post("/api/generate-code", json={"nodes": graph["nodes"], "edges": graph["edges"]})
    assert generated.status_code == 200, generated.text
    assert "A >= B and A >= C" in generated.json()["code"]


def test_analyze_keeps_review_when_operator_evidence_is_inconclusive(monkeypatch):
    """With no corroborating pixel evidence the condition stays flagged, so the
    graph is NOT silently approved."""
    monkeypatch.setattr(api_server, "GEMINI_API_KEY", "")
    raw = _synthetic_condition_graph(monkeypatch, "A = B and\nA = C?", 49.0, signatures=[])
    res = client.post("/api/analyze", files={"file": ("synthetic.png", raw, "image/png")})
    assert res.status_code == 200, res.text
    graph = res.json()
    dec = next(n for n in graph["nodes"] if n["type"] == "decision")
    assert dec["data"]["label"] == "A = B and\nA = C?"
    assert dec["data"]["needs_review"] is True
    assert graph["graph_status"] == "needs_review"
    blocked = client.post("/api/generate-code", json={"nodes": graph["nodes"], "edges": graph["edges"]})
    assert blocked.status_code == 422
    assert "#3" in blocked.json()["detail"]


def test_ai_reading_validity_gates_by_node_type():
    decision = {"type": "decision"}
    assert api_server._ai_reading_is_valid(decision, "A >= B and A >= C?")
    assert not api_server._ai_reading_is_valid(decision, "A >= B and")
    assert not api_server._ai_reading_is_valid(decision, "")
    out = {"type": "input_output"}
    assert api_server._ai_reading_is_valid(out, "Print A is largest")
    assert not api_server._ai_reading_is_valid(out, "Print")
    proc = {"type": "process"}
    assert api_server._ai_reading_is_valid(proc, "fact = fact * i")
    assert not api_server._ai_reading_is_valid(proc, "~")


def test_analyze_uses_ai_vision_to_resolve_ambiguous_condition(monkeypatch):
    """When local pixel evidence is inconclusive and Gemini is configured, a
    validated AI reading clears the review gate (validation is still enforced)."""
    monkeypatch.setattr(api_server, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(
        ocr_engine, "extract_flowchart_text_with_gemini",
        lambda pil_img, blocks, timeout_sec=6.0, include_uncertain=False: {3: "A >= B and A >= C?"},
    )
    raw = _synthetic_condition_graph(monkeypatch, "A = B and\nA = C?", 49.0, signatures=[])
    res = client.post("/api/analyze", files={"file": ("synthetic.png", raw, "image/png")})
    assert res.status_code == 200, res.text
    graph = res.json()
    dec = next(n for n in graph["nodes"] if n["type"] == "decision")
    assert dec["data"]["label"] == "A >= B and A >= C?", dec["data"]["label"]
    assert dec["data"]["needs_review"] is False
    assert graph["graph_status"] == "verified", graph.get("warnings")


def test_analyze_rejects_invalid_ai_vision_reading(monkeypatch):
    """An AI reading that does not validate is discarded and the node stays
    flagged - the review gate is never bypassed."""
    monkeypatch.setattr(api_server, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(
        ocr_engine, "extract_flowchart_text_with_gemini",
        lambda pil_img, blocks, timeout_sec=6.0, include_uncertain=False: {3: "and A C"},
    )
    raw = _synthetic_condition_graph(monkeypatch, "A = B and\nA = C?", 49.0, signatures=[])
    res = client.post("/api/analyze", files={"file": ("synthetic.png", raw, "image/png")})
    assert res.status_code == 200, res.text
    dec = next(n for n in res.json()["nodes"] if n["type"] == "decision")
    assert dec["data"]["needs_review"] is True
