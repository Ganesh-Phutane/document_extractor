"""
main.py
───────
FastAPI application entry point.
Mounts all routers and sets up middleware.

Run locally:
    uvicorn backend.main:app --reload --port 8000
    (from the project root: d:/FM/New folder/project/)
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

# ── App Instance ─────────────────────────────────────────
app = FastAPI(
    title="AI Document Processing Platform",
    description="Upload any document → AI extracts structured data → self-improves over time.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    root_path="/api",
)

# ── CORS ─────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://127.0.0.1",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────
from routes.auth import router as auth_router
from routes.documents import router as documents_router
from routes.extractions import router as extractions_router
from routes.templates import router as templates_router
from routes.master_data import router as master_data_router
# from routes.dashboard import router as dashboard_router
#
app.include_router(auth_router)
app.include_router(documents_router, prefix="/documents", tags=["Documents"])
app.include_router(extractions_router, prefix="/extractions", tags=["Extractions"])
app.include_router(templates_router,   prefix="/templates",   tags=["Templates"])
app.include_router(master_data_router, prefix="/master",      tags=["Master Data"])
# app.include_router(dashboard_router,   prefix="/dashboard",   tags=["Dashboard"])


# ── Health Check ─────────────────────────────────────────
@app.get("/health", tags=["Health"])
def health_check():
    """Quick check that the API is alive."""
    logger.info("Health check called")
    return {
        "status": "ok",
        "env": settings.APP_ENV,
        "version": "1.0.0",
    }


# ── Startup / Shutdown Events ────────────────────────────
@app.on_event("startup")
async def on_startup():
    logger.info("Application starting up", extra={"env": settings.APP_ENV})


@app.on_event("shutdown")
async def on_shutdown():
    logger.info("Application shutting down")
