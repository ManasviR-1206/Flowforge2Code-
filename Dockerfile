# Stage 1: Build Frontend (Vite + React)
FROM node:20-alpine AS frontend-builder
WORKDIR /app/landing
COPY landing/package*.json ./
RUN npm install
COPY landing/ .
RUN npm run build

# Stage 2: Production Python FastAPI Backend
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies required for OpenCV and Tesseract OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libglib2.0-0 \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend files
COPY *.py .

# Copy built frontend from Stage 1 into landing/dist
COPY --from=frontend-builder /app/landing/dist /app/landing/dist

# Expose port
EXPOSE 8000

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV DATABASE_URL="sqlite:///./flowforge.db"

# Start Uvicorn server
CMD ["python", "-m", "uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]
