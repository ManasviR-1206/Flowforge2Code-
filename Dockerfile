# Stage 1: Build Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/landing

COPY landing/package*.json ./
RUN npm ci
COPY landing/ ./
RUN npm run build

# Stage 2: FastAPI backend
FROM python:3.11-slim
WORKDIR /app

# OCR, OpenCV and sandbox system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    tesseract-ocr \
    bubblewrap \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY *.py ./
COPY --from=frontend-builder /app/landing/dist /app/landing/dist

ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV FLOWFORGE_EXECUTION=auto

EXPOSE 8000

CMD ["sh", "-c", "exec python -m uvicorn api_server:app --host 0.0.0.0 --port ${PORT:-8000}"]
