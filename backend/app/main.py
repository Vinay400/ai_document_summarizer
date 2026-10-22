"""
FastAPI application entry point.

Run from the `backend/` directory:

    .venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000

Interactive API docs: http://localhost:8000/docs
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import evaluate, health, summarize, upload
from app.config import settings

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown tasks.

    Heavy models (Sentence-Transformers, BART) are loaded once here from Phase 5
    onwards, rather than on every request.
    """
    settings.ensure_directories()
    logger.info("Starting %s v%s", settings.APP_NAME, settings.APP_VERSION)
    logger.info("Uploads: %s", settings.upload_dir)
    yield
    logger.info("Shutting down")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "Extractive, abstractive and hybrid summarization for long-form "
        "documents (PDF / DOCX / TXT), with ROUGE and BLEU evaluation."
    ),
    lifespan=lifespan,
)

# The React dev server (port 5173) and the API (port 8000) are different
# origins, so the browser blocks requests unless the API allows them.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Collapse FastAPI's verbose 422 body into one readable message.

    FastAPI normally returns a list of error objects; the front-end only ever
    has to render a single string.
    """
    problems = [
        f"{' -> '.join(str(p) for p in err.get('loc', ()) if p != 'body')}: {err.get('msg')}"
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422, content={"detail": "; ".join(problems) or "Invalid request."}
    )


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception):
    """Last resort: never leak a stack trace to the client.

    The traceback still goes to the server log, so debugging is unaffected.
    """
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Unexpected server error. See the backend log for details."},
    )


app.include_router(health.router, prefix="/api")
app.include_router(upload.router, prefix="/api")
app.include_router(summarize.router, prefix="/api")
app.include_router(evaluate.router, prefix="/api")


@app.get("/", tags=["System"], summary="Service banner")
async def root() -> dict:
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/api/health",
    }
