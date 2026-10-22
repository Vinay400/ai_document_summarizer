"""Business logic. Each module is framework-light and unit-testable.

    document_service    - PDF / DOCX / TXT extraction + text storage
    ocr_service         - Tesseract OCR wrapper
    cleaning_service    - text normalisation
    chunking_service    - sentence segmentation + sentence-aware chunking
    extractive_service  - embeddings + TextRank
    abstractive_service - transformer summarization        (Phase 6)
    hybrid_service      - extractive filter -> abstractive (Phase 7)
    evaluation_service  - ROUGE-1/2/L and BLEU             (Phase 8)
"""
