# FlowForge AI

Turn flowcharts into executable Python. The graph `{nodes, edges}` is the only source of truth: draw, upload, or describe a program → edit the flowchart → generate code → run it.

## Run locally

1. **Backend env**

   ```
   copy .env.example .env
   ```

   Put your Gemini key in `.env` as `GEMINI_API_KEY=...` (never in the frontend). If the key is missing, drawing, the structural debugger, and code execution still work; AI generate/chat show: *AI generation is currently unavailable. Please configure the backend API key.*

2. **Python API** (from the repo root)

   ```
   pip install -r requirements.txt
   uvicorn api_server:app --reload --port 8000
   ```

   Optional: install [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) so uploaded images get text labels.

3. **React workspace**

   ```
   cd landing
   npm install
   npm run dev
   ```

   Open the Vite URL (proxies `/api` to port 8000). Routes: `/` landing, `/workspace` editor.

## Pipeline

Prompt or image → flowchart JSON → logic engine → Python 3. Regenerating after you edit a node (for example `sum = a + b` → `sum = a * b`) updates the code from the graph, not from the original prompt.

## Verify

With the API running:

```
python test_api.py
```
