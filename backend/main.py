from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse

from backend.routers.events import router as events_router
from backend.services.predictor import predictor_service

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR = BASE_DIR / "uploads"
EXTENSION_DIR = BASE_DIR.parent / "extension"

STATIC_DIR.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
EXTENSION_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Warm up poster authenticity model
    print("==================================================")
    print(" EventTrust AI: Starting College Event Application")
    print("==================================================")
    try:
        predictor_service.warmup()
    except Exception as e:
        print(f"Warning: Model warmup failed: {e}")
    yield
    print("EventTrust AI: Application shutdown.")


app = FastAPI(
    title="EventTrust AI - College Event & Poster Verification API",
    description="Backend service for college event discovery and deep-learning poster authenticity verification with QR code detection and security analysis.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for cross-origin frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount uploaded files, static assets, and extension files
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/extension", StaticFiles(directory=str(EXTENSION_DIR)), name="extension")

# Include API Router
app.include_router(events_router)


@app.get("/api/health", summary="Health Check")
def health_check():
    return {
        "status": "healthy",
        "service": "EventTrust College Event Platform",
        "model_loaded": predictor_service.model is not None,
        "model_name": "poster_model.keras"
    }


@app.get("/", summary="College Event Web Application")
def index_page():
    index_html = STATIC_DIR / "index.html"
    if index_html.exists():
        return FileResponse(str(index_html))
    return JSONResponse({
        "message": "EventTrust AI College Event API is running.",
        "docs": "/docs",
        "events": "/api/events"
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
