import base64

from app.config import settings
from app.routers.finance import router as finance_router
from app.routers.fitness import router as fitness_router
from app.routers.registry import router as registry_router
from app.services.normalizer import normalize_extraction
from app.services.parser import parse_vision_response
from app.services.registry import VariableRegistry
from app.services.router import get_provider
from app.services.storage import save_session
from fastapi import FastAPI, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.params import File

app = FastAPI()

EXTRACTION_PROMPT = """Extract all fitness metrics from this image. Return ONLY valid JSON, no explanation:
{"workout_type": "string", "variables": {"name": {"value": "number or string", "unit": "string"}}}"""

# CORS (only in development)
if settings.environment == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(finance_router, prefix="/finance", tags=["finance"])
app.include_router(fitness_router, prefix="/fitness", tags=["fitness"])
app.include_router(registry_router, prefix="/registry", tags=["registry"])


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/log/training/session")
async def log_training_session(image: UploadFile = File(...), sensitive: bool = False):
    contents = await image.read()
    image_base64 = base64.b64encode(contents).decode()

    # Route to appropriate provider
    provider = get_provider(task="vision", sensitive=sensitive)
    raw = await provider.vision(image_base64, EXTRACTION_PROMPT)

    # Parse the model's response
    parsed = parse_vision_response(raw)

    # Save to file if parsing succeeded
    if "error" not in parsed:
        # Normalize variable names using registry
        registry = VariableRegistry(path="data/registry/variables.json")
        normalized = normalize_extraction(parsed, registry)
        parsed = normalized["normalized"]

        # Save normalized data to /data/sessions/
        storage_result = save_session(parsed)
    else:
        storage_result = {"id": None, "logged_to": None}
        normalized = {}
    return {
        "filename": image.filename,
        "parsed": parsed,
        "id": storage_result["id"],
        "logged_to": storage_result["logged_to"],
        "provider": provider.__class__.__name__,
        "unknown_variables": normalized.get("unknown", []),
        "stats": normalized.get("stats", {}),
    }
