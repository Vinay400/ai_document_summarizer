"""
POST /api/summarize - summarize a document that was already uploaded.

The document is referred to by the id from /api/upload, so switching mode or
length never re-uploads the file.
"""

import logging
import time

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from typing import Any

from app.models.schemas import (
    CompareSummarizeRequest,
    CompareSummarizeResponse,
    ErrorResponse,
    ModeSummaryResult,
    SummarizeRequest,
    SummarizeResponse,
)
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


def compute_summary_analytics(text: str, summary: str) -> dict[str, Any]:
    """Compute readability, key topics, and faithfulness analytics."""
    try:
        from app.services import analytics_service

        readability = analytics_service.compare_readability(text, summary)
        keyphrases = analytics_service.extract_keyphrases(text, top_k=6)
        faithfulness = analytics_service.check_faithfulness_and_attribution(text, summary)
        return {
            "readability": readability,
            "keyphrases": keyphrases,
            "faithfulness": faithfulness,
        }
    except Exception as exc:
        logger.warning("Analytics computation failed: %s", exc)
        return {}


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
    start_time = time.perf_counter()
    summary = await run_in_threadpool(summarizer, text, request.length)
    latency = round(time.perf_counter() - start_time, 3)

    # Compute advanced analytics (readability, key topics, hallucination check)
    analytics = await run_in_threadpool(compute_summary_analytics, text, summary)

    # Persist summary in SQLite history
    try:
        from app.services import history_service

        doc_words = len(text.split()) if text.strip() else 0
        words = len(summary.split()) if summary.strip() else 0
        chars = len(summary)
        comp_ratio = round((1.0 - (words / doc_words)) * 100.0, 1) if doc_words > 0 else 0.0

        history_service.save_summary(
            document_id=request.document_id,
            mode=request.mode,
            length=request.length,
            summary=summary,
            word_count=words,
            character_count=chars,
            compression_ratio=comp_ratio,
            latency_seconds=latency,
            analytics=analytics,
        )
    except Exception as exc:
        logger.warning("Failed to save summary to history database: %s", exc)

    return SummarizeResponse(
        document_id=request.document_id,
        mode=request.mode,
        length=request.length,
        summary=summary,
        analytics=analytics,
    )


@router.post(
    "/summarize/compare",
    response_model=CompareSummarizeResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Unknown document id"},
    },
    summary="Generate summaries for all three strategies (Extractive, Abstractive, Hybrid) for comparison",
)
async def compare_summarize_document(
    request: CompareSummarizeRequest,
) -> CompareSummarizeResponse:
    text, _metadata = document_service.load_document(request.document_id)
    doc_words = len(text.split())
    doc_chars = len(text)

    modes_result: dict[str, ModeSummaryResult] = {}
    for mode_name in ("extractive", "abstractive", "hybrid"):
        summarizer = SUMMARIZERS[mode_name]
        start_time = time.perf_counter()
        summary = await run_in_threadpool(summarizer, text, request.length)
        latency = round(time.perf_counter() - start_time, 3)

        words = len(summary.split()) if summary.strip() else 0
        chars = len(summary)
        compression = (
            round((1.0 - (words / doc_words)) * 100.0, 1) if doc_words > 0 else 0.0
        )

        analytics = await run_in_threadpool(compute_summary_analytics, text, summary)

        modes_result[mode_name] = ModeSummaryResult(
            mode=mode_name,
            summary=summary,
            word_count=words,
            character_count=chars,
            compression_ratio=compression,
            latency_seconds=latency,
            analytics=analytics,
        )

        try:
            from app.services import history_service

            history_service.save_summary(
                document_id=request.document_id,
                mode=mode_name,
                length=request.length,
                summary=summary,
                word_count=words,
                character_count=chars,
                compression_ratio=compression,
                latency_seconds=latency,
                analytics=analytics,
            )
        except Exception as exc:
            logger.warning("Failed to save mode summary to history database: %s", exc)

    return CompareSummarizeResponse(
        document_id=request.document_id,
        length=request.length,
        original_word_count=doc_words,
        original_character_count=doc_chars,
        modes=modes_result,
    )

