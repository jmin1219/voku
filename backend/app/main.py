"""
Voku v0.3 — Knowledge-first cognitive prosthetic

Backend entry point. Graph operations + LLM extraction pipeline.
"""

from app.config import settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Voku", version="0.3.0")

# CORS (development only)
if settings.environment == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


@app.get("/")
def read_root():
    return {"name": "Voku", "version": "0.3.0"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}
