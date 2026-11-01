"""
POST /api/chat - Interactive Question-Answering (RAG) on uploaded documents.

Allows users and examiners to chat with the document and verify facts directly.
"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from app.models.schemas import ChatRequest, ChatResponse, ErrorResponse
from app.services import document_service, qa_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Document Q&A"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Unknown document id"},
        400: {"model": ErrorResponse, "description": "Invalid question"},
    },
    summary="Ask a question about an uploaded document",
)
async def chat_with_document(request: ChatRequest) -> ChatResponse:
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    text, _metadata = document_service.load_document(request.document_id)

    # Retrieval and answer generation run in worker threadpool
    result = await run_in_threadpool(
        qa_service.answer_document_question, text, request.question
    )

    return ChatResponse(
        document_id=request.document_id,
        question=request.question,
        answer=result["answer"],
        confidence=result["confidence"],
        sources=result["sources"],
    )

