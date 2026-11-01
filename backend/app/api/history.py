"""
History and Export API endpoints.

Endpoints:
- GET /api/history - list past uploaded documents with summary stats
- GET /api/history/{document_id} - get full history for a document
- DELETE /api/history/{document_id} - remove from history
- POST /api/export/brief - generate a downloadable executive brief report
"""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException

from app.models.schemas import (
    ErrorResponse,
    ExportBriefRequest,
    ExportBriefResponse,
    HistoryItem,
    HistoryListResponse,
)
from app.services import document_service, history_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["History & Export"])


@router.get(
    "/history",
    response_model=HistoryListResponse,
    summary="List past uploaded documents and summaries",
)
async def list_history() -> HistoryListResponse:
    docs = history_service.list_documents()
    items = [
        HistoryItem(
            document_id=d["document_id"],
            filename=d["filename"],
            file_type=d["file_type"],
            character_count=d["character_count"],
            word_count=d["word_count"],
            page_count=d.get("page_count"),
            ocr_used=bool(d.get("ocr_used", 0)),
            extraction_method=d.get("extraction_method", ""),
            preview=d.get("preview", ""),
            created_at=d["created_at"],
            summary_count=d.get("summary_count", 0),
        )
        for d in docs
    ]
    return HistoryListResponse(documents=items)


@router.get(
    "/history/{document_id}",
    responses={404: {"model": ErrorResponse, "description": "Document not found"}},
    summary="Get full history for a specific document",
)
async def get_history_detail(document_id: str) -> dict[str, Any]:
    record = history_service.get_document_history(document_id)
    if not record:
        raise HTTPException(status_code=404, detail="Document history not found.")
    return record


@router.delete(
    "/history/{document_id}",
    responses={404: {"model": ErrorResponse, "description": "Document not found"}},
    summary="Delete a document and its summaries from history",
)
async def delete_history_item(document_id: str) -> dict[str, str]:
    deleted = history_service.delete_document_history(document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found.")
    return {"message": "Document removed from history successfully."}


@router.post(
    "/export/brief",
    response_model=ExportBriefResponse,
    responses={404: {"model": ErrorResponse, "description": "Document not found"}},
    summary="Generate a formatted Executive Summary Report",
)
async def export_executive_brief(request: ExportBriefRequest) -> ExportBriefResponse:
    text, metadata = document_service.load_document(request.document_id)
    record = history_service.get_document_history(request.document_id)

    # Find the most relevant summary
    target_summary = None
    if record and record.get("summaries"):
        for s in record["summaries"]:
            if s["mode"] == request.mode and s["length"] == request.length:
                target_summary = s
                break
        if not target_summary:
            target_summary = record["summaries"][0]

    filename = metadata.get("filename", "Document")
    summary_text = target_summary["summary"] if target_summary else text[:500] + "..."
    mode_str = target_summary["mode"].title() if target_summary else request.mode.title()

    analytics = target_summary.get("analytics") if target_summary else None
    readability = analytics.get("readability") if analytics else None
    keyphrases = analytics.get("keyphrases") if analytics else []
    faithfulness = analytics.get("faithfulness") if analytics else None

    # Construct Markdown Report
    md_lines = [
        f"# EXECUTIVE SUMMARY REPORT",
        f"**Source Document:** {filename}  ",
        f"**Strategy:** {mode_str} Summarization ({request.length.title()})  ",
        f"**Original Word Count:** {len(text.split()):,} words  ",
        f"**Summary Word Count:** {len(summary_text.split()):,} words  ",
        "",
        "---",
        "",
        "## Key Topical Themes",
        ", ".join([f"`{k}`" for k in keyphrases]) if keyphrases else "General Topic",
        "",
        "## Executive Summary",
        summary_text,
        "",
        "---",
        "",
        "## Analytical Metrics & Quality Assurance",
    ]

    if readability:
        md_lines.extend([
            f"* **Reading Time Saved:** {readability.get('time_saved_percent', 0)}% "
            f"({readability.get('time_saved_seconds', 0)} seconds)",
            f"* **Summary Reading Level:** {readability.get('summary', {}).get('reading_level', 'Standard')}",
            f"* **Flesch Reading Ease:** {readability.get('summary', {}).get('flesch_reading_ease', 0)} / 100",
        ])

    if faithfulness:
        md_lines.extend([
            f"* **Factuality & Hallucination Guardrail:** {faithfulness.get('overall_confidence', 100)}% Confidence "
            f"({faithfulness.get('hallucination_risk', 'low').upper()} Hallucination Risk)",
            f"* **Grounded Sentences:** {faithfulness.get('grounded_count', 0)} / {faithfulness.get('total_summary_sentences', 0)}",
        ])

    md_lines.extend([
        "",
        "---",
        "*Generated by AI Document Summarization Platform — MCA Major Project*",
    ])

    markdown_content = "\n".join(md_lines)

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>Executive Brief - {filename}</title>
      <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; max-width: 800px; margin: 40px auto; padding: 0 20px; color: #1e293b; }}
        h1 {{ color: #0f172a; border-bottom: 2px solid #e2e8f0; padding-bottom: 12px; }}
        h2 {{ color: #1e3a8a; margin-top: 28px; }}
        .badge {{ background: #eff6ff; color: #1d4ed8; padding: 3px 8px; border-radius: 4px; font-size: 0.85em; font-weight: 600; display: inline-block; margin-right: 6px; }}
        .summary-box {{ background: #f8fafc; border-left: 4px solid #3b82f6; padding: 18px; border-radius: 4px; margin: 20px 0; font-size: 1.05em; }}
        .metrics-table {{ width: 100%; border-collapse: collapse; margin-top: 14px; font-size: 0.9em; }}
        .metrics-table td, .metrics-table th {{ border: 1px solid #cbd5e1; padding: 8px 12px; }}
        .metrics-table th {{ background: #f1f5f9; text-align: left; }}
        .footer {{ margin-top: 40px; font-size: 0.8em; color: #64748b; border-top: 1px solid #e2e8f0; padding-top: 12px; }}
      </style>
    </head>
    <body>
      <h1>Executive Summary Report</h1>
      <p><strong>Source Document:</strong> {filename}<br>
      <strong>Summarization Strategy:</strong> {mode_str} ({request.length.title()})<br>
      <strong>Compression:</strong> {len(text.split()):,} words &rarr; {len(summary_text.split()):,} words</p>

      <h2>Key Topics</h2>
      <div>
        {' '.join([f'<span class="badge">{k}</span>' for k in keyphrases]) if keyphrases else '<span>General</span>'}
      </div>

      <h2>Executive Summary</h2>
      <div class="summary-box">
        {summary_text.replace(chr(10), '<br><br>')}
      </div>

      <h2>Quality &amp; Readability Metrics</h2>
      <table class="metrics-table">
        <tr><th>Metric</th><th>Value</th><th>Interpretation</th></tr>
        <tr><td>Reading Time Saved</td><td>{readability.get('time_saved_percent', 0) if readability else 0}%</td><td>Direct user efficiency gain</td></tr>
        <tr><td>Reading Ease Score</td><td>{readability.get('summary', {}).get('flesch_reading_ease', 0) if readability else 0} / 100</td><td>{readability.get('summary', {}).get('reading_level', 'Standard') if readability else 'Standard'}</td></tr>
        <tr><td>Factuality Confidence</td><td>{faithfulness.get('overall_confidence', 100) if faithfulness else 100}%</td><td>{faithfulness.get('hallucination_risk', 'low').upper() if faithfulness else 'LOW'} Risk</td></tr>
      </table>

      <div class="footer">
        Generated by AI Document Summarization Platform &middot; MCA Final Project
      </div>
    </body>
    </html>
    """

    return ExportBriefResponse(
        document_id=request.document_id,
        filename=filename,
        markdown=markdown_content,
        html=html_content,
    )

