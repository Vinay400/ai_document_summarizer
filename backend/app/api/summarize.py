"""
POST /api/summarize - summarize a document that was already uploaded.

The document is referred to by the id from /api/upload, so switching mode or
length never re-uploads the file.
"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.models.schemas import ErrorResponse, SummarizeRequest, SummarizeResponse
from app.services import (
    abstractive_service,
    document_service,
    extractive_service,
    hybrid_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Summarization"])

SUMMARIZERS = {
    "extractive": extractive_service.summarize,
    "abstractive": abstractive_service.summarize,
    "hybrid": hybrid_service.summarize,
}


@router.post(
    "/summarize",
    response_model=SummarizeResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Unknown document id"},
        501: {"model": ErrorResponse, "description": "Mode not implemented yet"},
    },
    summary="Summarize an uploaded document",
)
async def summarize_document(request: SummarizeRequest) -> SummarizeResponse:
    summarizer = SUMMARIZERS.get(request.mode)
    if summarizer is None:
        raise HTTPException(
            status_code=501,
            detail=f"Summarization mode '{request.mode}' is not implemented yet.",
        )

    text, _metadata = document_service.load_document(request.document_id)

    # Model inference is blocking CPU work, so it runs in a worker thread.
    summary = await run_in_threadpool(summarizer, text, request.length)

    return SummarizeResponse(
        document_id=request.document_id,
        mode=request.mode,
        length=request.length,
        summary=summary,
    )
