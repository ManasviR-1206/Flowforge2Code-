"""
Streamlit is no longer user-facing. Use the React workspace + FastAPI backend.

  copy .env.example to .env  (set GEMINI_API_KEY)
  pip install -r requirements.txt
  uvicorn api_server:app --reload --port 8000
  cd landing && npm install && npm run dev
"""

if __name__ == "__main__":
    print(__doc__)
    raise SystemExit(
        "The Streamlit UI has been removed. Start the FastAPI server "
        "(uvicorn api_server:app --port 8000) and the Vite app in landing/."
    )
