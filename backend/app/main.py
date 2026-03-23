"""
FastAPI main application — VCF Interpretation Agent Backend
"""
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import create_tables
from app.api.routes.upload import router as upload_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.variants import router as variants_router
from app.api.routes.chat import router as chat_router
from app.api.routes.report import router as report_router
from app.api.routes.audit import router as audit_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create database tables."""
    logger.info("Starting VCF Interpretation Agent backend...")
    await create_tables()
    logger.info("Database tables initialized.")
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="VCF Interpretation Agent",
    description=(
        "Evidence-grounded multi-agent platform for clinical and research "
        "variant analysis. Combines deterministic bioinformatics processing "
        "with Gemini AI for explainable variant interpretation."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Register routers
app.include_router(upload_router, prefix="/api", tags=["Upload"])
app.include_router(jobs_router, prefix="/api/jobs", tags=["Jobs"])
app.include_router(variants_router, prefix="/api/jobs", tags=["Variants"])
app.include_router(chat_router, prefix="/api/chat", tags=["Agent Chat"])
app.include_router(report_router, prefix="/api/jobs", tags=["Reports"])
app.include_router(audit_router, prefix="/api/jobs", tags=["Audit"])


@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "VCF Interpretation Agent",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
async def health():
    return {"status": "ok"}
