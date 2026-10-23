# syntax=docker/dockerfile:1

# ---------------------------------------------------------------------------
# Stage 1 - build the React/Vite frontend into landing/dist
# ---------------------------------------------------------------------------
FROM node:20-alpine AS frontend-builder
WORKDIR /app/landing

COPY landing/package*.json ./
RUN npm ci
COPY landing/ ./
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2 - FastAPI backend (serves landing/dist and the /api routes)
# ---------------------------------------------------------------------------
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    FLOWFORGE_EXECUTION=auto \
    PORT=8000 \
    FLOWFORGE_SERVICE=api

# System dependencies:
#   libgl1, libglib2.0-0 .............. OpenCV runtime for the OCR pipeline
#   tesseract-ocr, tesseract-ocr-eng .. OCR engine and English traineddata
#   bubblewrap ........................ the executor sandbox (auto/sandbox mode)
#   libcap2-bin ....................... getcap, used below to prove bwrap is unprivileged
#   ca-certificates ................... TLS for the optional Gemini API
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        tesseract-ocr \
        tesseract-ocr-eng \
        bubblewrap \
        libcap2-bin \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# bubblewrap must stay an unprivileged binary: the executor's security model relies on
# plain user namespaces plus --cap-drop ALL / --disable-userns inside the sandbox, not on
# a setuid helper. Fail the build if the distro ships it setuid or with file capabilities.
RUN set -eux; \
    chmod 0755 /usr/bin/bwrap; \
    if [ -n "$(getcap /usr/bin/bwrap)" ]; then \
        echo "ERROR: /usr/bin/bwrap must not carry file capabilities" >&2; exit 1; \
    fi

# Non-root runtime user. The sandbox self-test requires this: RLIMIT_NPROC (and several
# other limits) are not enforced for uid 0, so running as root would make the executor
# report the sandbox as unavailable instead of silently weakening it.
RUN useradd --uid 10001 --create-home --shell /usr/sbin/nologin flowforge
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py ./
COPY --from=frontend-builder /app/landing/dist ./landing/dist

# Application code stays root-owned and read-only for the runtime user.
RUN chmod -R a+rX /app

USER flowforge
WORKDIR /app

EXPOSE 8000 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.getenv('PORT', '8000') + '/api/health', timeout=4)" || exit 1

# Render injects PORT. FLOWFORGE_SERVICE selects the entrypoint:
#   api        -> FastAPI API + SPA (default)
#   runner     -> isolated remote execution runner
CMD ["sh", "-c", "if [ \"${FLOWFORGE_SERVICE}\" = \"runner\" ]; then exec python -m uvicorn runner_server:app --host 0.0.0.0 --port ${PORT:-8001}; else exec python -m uvicorn api_server:app --host 0.0.0.0 --port ${PORT:-8000}; fi"]
