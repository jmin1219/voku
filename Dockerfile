# ──────────────────────────────────────────────
# Stage 1: Build frontend
# ──────────────────────────────────────────────
FROM node:20-slim AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ ./

# Production API is same-origin: /api
ENV VITE_API_BASE=/api
RUN npm run build

# ──────────────────────────────────────────────
# Stage 2: Python runtime
# ──────────────────────────────────────────────
FROM python:3.13-slim AS runtime

WORKDIR /app

# System deps for numpy/scipy
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download embedding model (~420MB) so it's baked into the image
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-base-en-v1.5')"

# Copy backend code
COPY backend/app ./app
COPY backend/migrations ./migrations
COPY backend/scripts ./scripts
COPY backend/pytest.ini ./

# Seed a SYNTHETIC demo DB into the image at build time — offline (local BGE, no API keys),
# all data invented ("Mina Park"), safe to deploy publicly. App reads ./data/voku.db (default db_path),
# so a fresh ephemeral deploy (HF Spaces) boots with a populated graph instead of an empty demo.
RUN mkdir -p ./data \
 && python scripts/seed_demo.py --db-path ./data/voku.db

# Copy built frontend
COPY --from=frontend-build /app/frontend/dist ./static

# Environment defaults
ENV ENVIRONMENT=production
ENV VOKU_PROVIDER=groq

EXPOSE 8000

# Shell form so $PORT (injected by Railway/host) expands; falls back to 8000 locally.
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
