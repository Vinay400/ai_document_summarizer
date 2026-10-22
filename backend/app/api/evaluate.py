"""
POST /api/evaluate - generate a summary and evaluate it against a reference text.

The document is referred to by the id from /api/upload. The requested mode
summarizes the document, and the result is scored against the user-provided
reference summary using ROUGE-1/2/L and BLEU.
"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.api.summarize import SUMMARIZERS
from app.models.schemas import ErrorResponse, EvaluateRequest, EvaluateResponse
from app.services import document_service, evaluation_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Evaluation"])


@router.post(
    "/evaluate",
    response_model=EvaluateResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Unknown document id"},
        501: {"model": ErrorResponse, "description": "Mode not implemented yet"},
    },
    summary="Evaluate summary against a reference text",
)
async def evaluate_document(request: EvaluateRequest) -> EvaluateResponse:
    summarizer = SUMMARIZERS.get(request.mode)
    if summarizer is None:
        raise HTTPException(
            status_code=501,
            detail=f"Summarization mode '{request.mode}' is not implemented yet.",
        )

    text, _metadata = document_service.load_document(request.document_id)

    # Summarization model inference and scoring run in worker thread pool
    summary = await run_in_threadpool(summarizer, text, request.length)
    scores = await run_in_threadpool(
        evaluation_service.evaluate, summary, request.reference
    )

    return EvaluateResponse(
        document_id=request.document_id,
        mode=request.mode,
        length=request.length,
        summary=summary,
        reference=request.reference,
        metrics=scores,
    )
