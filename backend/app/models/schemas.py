"""
Pydantic request/response models.

These define the API's public shape. FastAPI validates requests against them,
serialises responses through them (so only declared fields are ever sent), and
generates the OpenAPI docs at `/docs` from them.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field

# Declaring these once means a typo like mode="extractiv" is rejected at the
# boundary with HTTP 422 instead of failing deep inside a service.
SummarizationMode = Literal["extractive", "abstractive", "hybrid"]
SummaryLength = Literal["short", "medium", "long"]


class CleaningInfo(BaseModel):
    """What the cleaning step changed, so its effect is visible, not silent.

    Cleaning removes page numbers and running headers/footers and rejoins words
    broken across a line. Showing the counts lets the user confirm that the
    document was read correctly rather than silently mangled.
    """

    raw_character_count: int = Field(description="Characters before cleaning.")
    removed_line_count: int = Field(
        default=0, description="Page numbers and repeated header/footer lines removed."
    )
    hyphenation_joins: int = Field(
        default=0, description="Words rejoined across a line break."
    )


class UploadResponse(BaseModel):
    """Metadata for a successfully ingested document.

    Note what is absent: the extracted text. The document is stored server-side
    under `document_id` and referred to by that id from then on.
    """

    document_id: str = Field(description="Handle used to summarize this document.")
    filename: str = Field(description="Sanitised original filename, for display.")
    file_type: str = Field(description="pdf, docx or txt.")
    character_count: int = Field(description="Characters of cleaned text.")
    word_count: int = Field(description="Words of cleaned text.")
    chunk_count: int = Field(
        default=0,
        description="Chunks the document is split into for summarization, using "
        "the current CHUNK_SIZE / CHUNK_OVERLAP settings.",
    )
    page_count: int | None = Field(
        default=None,
        description="Page count for PDFs; null for DOCX/TXT, whose page breaks "
        "cannot be determined reliably.",
    )
    ocr_used: bool = Field(description="Whether OCR was needed to recover the text.")
    extraction_method: str = Field(description="How the text was obtained.")
    cleaning: CleaningInfo = Field(description="What cleaning removed or repaired.")
    preview: str = Field(default="", description="First ~280 characters of the text.")
    warnings: list[str] = Field(
        default_factory=list, description="Non-fatal issues, e.g. image-only pages."
    )


class SummarizeRequest(BaseModel):
    """Ask for a summary of a document that was already uploaded."""

    document_id: str = Field(description="Id returned by /api/upload.")
    mode: SummarizationMode = Field(
        default="extractive", description="Which strategy to use."
    )
    length: SummaryLength = Field(
        default="medium", description="Roughly how long the summary should be."
    )


class SummarizeResponse(BaseModel):
    document_id: str
    mode: SummarizationMode
    length: SummaryLength
    summary: str = Field(description="The generated summary text.")
    analytics: dict[str, Any] | None = Field(
        default=None, description="Readability, keyphrases, and faithfulness score."
    )


class ErrorResponse(BaseModel):
    """The single error shape every failing endpoint returns."""

    detail: str = Field(description="Human-readable explanation for the user.")


class EvaluationMetrics(BaseModel):
    rouge_1: float = Field(description="ROUGE-1 F1-score (0.0 to 1.0).")
    rouge_2: float = Field(description="ROUGE-2 F1-score (0.0 to 1.0).")
    rouge_l: float = Field(description="ROUGE-L F1-score (0.0 to 1.0).")
    bleu: float = Field(description="BLEU score (0.0 to 100.0).")


class EvaluateRequest(BaseModel):
    """Ask for evaluation of a document summary against a reference text."""

    document_id: str = Field(description="Id returned by /api/upload.")
    reference: str = Field(description="Reference summary text to evaluate against.")
    mode: SummarizationMode = Field(
        default="extractive", description="Which summarization strategy to use."
    )
    length: SummaryLength = Field(
        default="medium", description="Roughly how long the summary should be."
    )


class EvaluateResponse(BaseModel):
    document_id: str
    mode: SummarizationMode
    length: SummaryLength
    summary: str = Field(description="The generated summary text.")
    reference: str = Field(description="The reference summary text.")
    metrics: EvaluationMetrics = Field(description="Calculated ROUGE and BLEU metrics.")


class ModeSummaryResult(BaseModel):
    mode: SummarizationMode
    summary: str = Field(description="The generated summary text.")
    word_count: int = Field(description="Word count of the summary.")
    character_count: int = Field(description="Character count of the summary.")
    compression_ratio: float = Field(
        description="Percentage reduction from original document word count."
    )
    latency_seconds: float = Field(description="Execution latency in seconds.")
    analytics: dict[str, Any] | None = Field(
        default=None, description="Readability, keyphrases, and faithfulness score."
    )


class CompareSummarizeRequest(BaseModel):
    document_id: str = Field(description="Id returned by /api/upload.")
    length: SummaryLength = Field(
        default="medium", description="Target summary length for all modes."
    )


class CompareSummarizeResponse(BaseModel):
    document_id: str
    length: SummaryLength
    original_word_count: int = Field(description="Word count of source document.")
    original_character_count: int = Field(description="Character count of source document.")
    modes: dict[str, ModeSummaryResult] = Field(
        description="Results for each strategy (extractive, abstractive, hybrid)."
    )


class ModeEvaluateResult(BaseModel):
    mode: SummarizationMode
    summary: str
    word_count: int
    character_count: int
    compression_ratio: float
    latency_seconds: float
    metrics: EvaluationMetrics


class CompareEvaluateRequest(BaseModel):
    document_id: str = Field(description="Id returned by /api/upload.")
    reference: str = Field(description="Ground-truth reference summary text.")
    length: SummaryLength = Field(
        default="medium", description="Target summary length for all modes."
    )
    summaries: dict[str, str] | None = Field(
        default=None,
        description="Optional precomputed summaries per mode to skip regeneration.",
    )


class CompareEvaluateResponse(BaseModel):
    document_id: str
    length: SummaryLength
    reference: str
    original_word_count: int
    modes: dict[str, ModeEvaluateResult]


class ChatRequest(BaseModel):
    document_id: str = Field(description="Document ID returned by /api/upload.")
    question: str = Field(description="User question about the document.")


class ChatResponse(BaseModel):
    document_id: str
    question: str
    answer: str
    confidence: float
    sources: list[str]


class HistoryItem(BaseModel):
    document_id: str
    filename: str
    file_type: str
    character_count: int
    word_count: int
    page_count: int | None = None
    ocr_used: bool = False
    extraction_method: str = ""
    preview: str = ""
    created_at: str
    summary_count: int = 0


class HistoryListResponse(BaseModel):
    documents: list[HistoryItem]


class ExportBriefRequest(BaseModel):
    document_id: str
    mode: SummarizationMode = "extractive"
    length: SummaryLength = "medium"


class ExportBriefResponse(BaseModel):
    document_id: str
    filename: str
    markdown: str
    html: str



