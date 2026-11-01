"""
POST /api/evaluate - generate a summary and evaluate it against a reference text.

The document is referred to by the id from /api/upload. The requested mode
summarizes the document, and the result is scored against the user-provided
reference summary using ROUGE-1/2/L and BLEU.
"""

import logging
import time

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.api.summarize import SUMMARIZERS
from app.models.schemas import (
    CompareEvaluateRequest,
    CompareEvaluateResponse,
    ErrorResponse,
    EvaluateRequest,
    EvaluateResponse,
    ModeEvaluateResult,
)
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

    try:
        from app.services import history_service

        history_service.save_evaluation(
            document_id=request.document_id,
            mode=request.mode,
            length=request.length,
            metrics=scores,
        )
    except Exception as exc:
        logger.warning("Failed to save evaluation to history database: %s", exc)

    return EvaluateResponse(
        document_id=request.document_id,
        mode=request.mode,
        length=request.length,
        summary=summary,
        reference=request.reference,
        metrics=scores,
    )


@router.post(
    "/evaluate/compare",
    response_model=CompareEvaluateResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Unknown document id"},
    },
    summary="Evaluate summaries across all 3 strategies against a reference text",
)
async def compare_evaluate_document(
    request: CompareEvaluateRequest,
) -> CompareEvaluateResponse:
    text, _metadata = document_service.load_document(request.document_id)
    doc_words = len(text.split())

    results: dict[str, ModeEvaluateResult] = {}
    for mode_name in ("extractive", "abstractive", "hybrid"):
        # If precomputed summary was provided, reuse it; otherwise generate
        if (
            request.summaries
            and mode_name in request.summaries
            and request.summaries[mode_name]
        ):
            summary = request.summaries[mode_name]
            latency = 0.0
        else:
            summarizer = SUMMARIZERS[mode_name]
            start_time = time.perf_counter()
            summary = await run_in_threadpool(summarizer, text, request.length)
            latency = round(time.perf_counter() - start_time, 3)

        words = len(summary.split()) if summary.strip() else 0
        chars = len(summary)
        compression = (
            round((1.0 - (words / doc_words)) * 100.0, 1) if doc_words > 0 else 0.0
        )

        scores = await run_in_threadpool(
            evaluation_service.evaluate, summary, request.reference
        )

        results[mode_name] = ModeEvaluateResult(
            mode=mode_name,
            summary=summary,
            word_count=words,
            character_count=chars,
            compression_ratio=compression,
            latency_seconds=latency,
            metrics=scores,
        )

    return CompareEvaluateResponse(
        document_id=request.document_id,
        length=request.length,
        reference=request.reference,
        original_word_count=doc_words,
        modes=results,
    )

