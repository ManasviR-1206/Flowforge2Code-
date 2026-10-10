# FlowForge AI

Turn flowcharts into executable Python. The graph `{nodes, edges}` is the only source of truth: draw, upload, or describe a program → edit the flowchart → generate code → run it.

## Run locally on one host

1. **Backend env**

   ```
   copy .env.example .env
   ```

   Put your Gemini key in `.env` as `GEMINI_API_KEY=...` (never in the frontend). If the key is missing, drawing, the structural debugger, and code execution still work; AI generate/chat show: *AI generation is currently unavailable. Please configure the backend API key.*

2. **Build the frontend**

   ```powershell
   cd landing
   npm install
   npm run build
   cd ..
   ```

3. **Run the combined app** (from the repo root)

   ```
   pip install -r requirements.txt
   uvicorn api_server:app --host 0.0.0.0 --port 8000
   ```

   Open `http://localhost:8000/`. FastAPI serves the frontend and `/api/*` routes from this same host; `/` is the landing page and `/workspace` is the editor. Rebuild the frontend after changing it, then restart FastAPI.

   Optional: install [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) so uploaded images get text labels.

## Frontend development (optional)

For Vite hot reload, run the API on port 8000 and use a second terminal:

   ```powershell
   cd landing
   npm run dev
   ```

   Open the Vite URL; `/api` requests are proxied to the backend.

## Pipeline

Prompt or image → flowchart JSON → logic engine → Python 3. Regenerating after you edit a node (for example `sum = a + b` → `sum = a * b`) updates the code from the graph, not from the original prompt.

## Verify

With the API running:

```
python test_api.py
```
