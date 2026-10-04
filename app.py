import os
import json
import cv2
import numpy as np
from PIL import Image
import streamlit as st
from streamlit_drawable_canvas import st_canvas

import cv_engine
import ocr_engine
import logic_engine
import llm_generator
import executor

# Page Configuration
st.set_page_config(
    page_title="Flowchart → Python Code",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-header { font-size: 2.2rem; font-weight: 700; color: #1E88E5; margin-bottom: 0px; }
    .sub-header { font-size: 1rem; color: #555555; margin-bottom: 20px; }
    .stCodeBlock { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-header">⚡ Flowchart to Executable Code Generator</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Team 5 | Transform visual flowcharts into clean, executable Python programs instantaneously.</p>', unsafe_allow_html=True)

# Sidebar Options
with st.sidebar:
    st.header("⚙️ Settings & Configuration")
    gemini_api_key = st.text_input("Google Gemini API Key (Optional)", type="password", help="If left empty, a rule-based AST compiler will generate the Python code.")
    
    st.divider()
    st.header("📌 Input Mode")
    input_choice = st.radio("Choose Flowchart Input Source:", ["Upload Flowchart Image", "Draw on Interactive Canvas", "Load Sample Flowchart"])
    
    st.divider()
    st.info("ℹ️ **Supported Symbols:**\n- **Oval / Stadium:** Start / End\n- **Rectangle:** Process / Action\n- **Parallelogram:** Input / Output\n- **Diamond:** Decision / Conditional")

# Helper function to generate sample flowcharts synthetically
def get_sample_flowchart(name):
    canvas = np.ones((500, 400, 3), dtype=np.uint8) * 255
    # Start block
    cv2.ellipse(canvas, (200, 50), (60, 25), 0, 0, 360, (0, 180, 0), 2)
    cv2.putText(canvas, "Start", (180, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 180, 0), 2)
    
    # Arrow 1
    cv2.arrowedLine(canvas, (200, 75), (200, 120), (0, 0, 0), 2, tipLength=0.2)
    
    # Input block
    pts = np.array([[130, 120], [270, 120], [240, 160], [100, 160]], np.int32)
    cv2.polylines(canvas, [pts], True, (255, 0, 255), 2)
    cv2.putText(canvas, "Input n", (150, 145), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 255), 2)

    # Arrow 2
    cv2.arrowedLine(canvas, (200, 160), (200, 210), (0, 0, 0), 2, tipLength=0.2)

    # Decision block
    d_pts = np.array([[200, 210], [270, 250], [200, 290], [130, 250]], np.int32)
    cv2.polylines(canvas, [d_pts], True, (0, 200, 200), 2)
    cv2.putText(canvas, "n > 0?", (175, 255), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 150, 150), 2)

    # Arrow 3 (Yes branch)
    cv2.arrowedLine(canvas, (200, 290), (200, 340), (0, 0, 0), 2, tipLength=0.2)
    cv2.putText(canvas, "Yes", (210, 315), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1)

    # Output block
    o_pts = np.array([[130, 340], [270, 340], [240, 380], [100, 380]], np.int32)
    cv2.polylines(canvas, [o_pts], True, (255, 0, 255), 2)
    cv2.putText(canvas, "Print Positive", (135, 365), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 0, 255), 2)

    # Arrow 4
    cv2.arrowedLine(canvas, (200, 380), (200, 430), (0, 0, 0), 2, tipLength=0.2)

    # End block
    cv2.ellipse(canvas, (200, 455), (60, 25), 0, 0, 360, (0, 0, 255), 2)
    cv2.putText(canvas, "End", (185, 460), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

    return Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB))

col_left, col_right = st.columns([1, 1])

raw_image = None

with col_left:
    st.subheader("1. Flowchart Input")
    
    if input_choice == "Upload Flowchart Image":
        uploaded_file = st.file_uploader("Choose a flowchart image file", type=["png", "jpg", "jpeg"])
        if uploaded_file:
            raw_image = Image.open(uploaded_file)
            st.image(raw_image, caption="Uploaded Flowchart Image", use_container_width=True)

    elif input_choice == "Draw on Interactive Canvas":
        st.caption("Draw your flowchart shapes below:")
        canvas_result = st_canvas(
            fill_color="rgba(255, 165, 0, 0.2)",
            stroke_width=3,
            stroke_color="#000000",
            background_color="#FFFFFF",
            height=480,
            drawing_mode="freedraw",
            key="sketch_canvas",
        )
        if canvas_result.image_data is not None:
            canvas_img = Image.fromarray(canvas_result.image_data.astype('uint8'), 'RGBA').convert('RGB')
            # Only process if user has drawn something
            if np.mean(np.array(canvas_img)) < 254:
                raw_image = canvas_img

    elif input_choice == "Load Sample Flowchart":
        sample_name = st.selectbox("Select Sample Template:", ["Positive Number Check"])
        raw_image = get_sample_flowchart(sample_name)
        st.image(raw_image, caption=f"Sample: {sample_name}", use_container_width=True)

with col_right:
    st.subheader("2. Computer Vision & OCR Analysis")
    
    if raw_image is not None:
        with st.spinner("Processing image and detecting flowchart shapes..."):
            norm_img = cv_engine.normalize_image(raw_image)
            blocks, thresh = cv_engine.detect_symbols(norm_img)
            connections = cv_engine.detect_connections(thresh, blocks)

            # Perform OCR on each block
            for b in blocks:
                ocr_text = ocr_engine.extract_block_text(norm_img, b["bbox"])
                b["text"] = ocr_text

            overlay_img = cv_engine.overlay_detections(norm_img, blocks, connections)
            st.image(cv2.cvtColor(overlay_img, cv2.COLOR_BGR2RGB), caption=f"Detected {len(blocks)} Blocks & {len(connections)} Connectors", use_container_width=True)

            # Editable Verification Table
            st.subheader("3. Verification & Edit Extracted Data")
            st.caption("Review extracted block labels and shapes below. Edit values if needed:")
            
            table_data = []
            for b in blocks:
                table_data.append({
                    "Block ID": b["id"],
                    "Shape Type": b["type"],
                    "Extracted Text": b["text"]
                })

            edited_df = st.data_editor(
                table_data,
                column_config={
                    "Block ID": st.column_config.NumberColumn(disabled=True),
                    "Shape Type": st.column_config.SelectboxColumn("Shape Type", options=["start_end", "process", "decision", "input_output"]),
                    "Extracted Text": st.column_config.TextColumn("Extracted Text")
                },
                use_container_width=True,
                num_rows="fixed"
            )

            # Update blocks with edits
            for row in edited_df:
                b_id = row["Block ID"]
                for b in blocks:
                    if b["id"] == b_id:
                        b["type"] = row["Shape Type"]
                        b["text"] = row["Extracted Text"]

            # Logic AST Reconstruction
            ast = logic_engine.build_flowchart_ast(blocks, connections)

            st.subheader("4. Code Generation & Execution")
            
            if st.button("🚀 Generate Python Code", type="primary", use_container_width=True):
                with st.spinner("Generating executable Python code via AI..."):
                    generated_code = llm_generator.generate_python_code(ast, gemini_api_key)
                    st.session_state["generated_code"] = generated_code

            if "generated_code" in st.session_state:
                code_to_show = st.session_state["generated_code"]
                st.code(code_to_show, language="python")

                st.subheader("5. Interactive Sandbox Testing")
                user_input_val = st.text_input("Program Input (if your code asks for input):", value="5")
                
                if st.button("▶️ Run Generated Code", use_container_width=True):
                    with st.spinner("Running code in safe sandbox..."):
                        execution_output = executor.run_code_safely(code_to_show, user_input_val, timeout_sec=3)
                        st.markdown("**Execution Output:**")
                        st.code(execution_output, language="text")
    else:
        st.info("👈 Upload an image, draw on canvas, or select a sample flowchart from the left sidebar to begin.")
