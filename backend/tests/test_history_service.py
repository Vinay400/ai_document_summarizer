"""
Unit tests for history_service (SQLite persistence).
"""

from app.services import history_service


def test_history_crud(tmp_path, monkeypatch):
    test_db = tmp_path / "test_history.db"
    monkeypatch.setattr(history_service, "DB_PATH", test_db)

    # 1. Save document
    doc_id = "test_doc_123"
    history_service.save_document(
        document_id=doc_id,
        filename="report.pdf",
        file_type="pdf",
        character_count=1200,
        word_count=200,
        page_count=2,
        ocr_used=False,
        extraction_method="pymupdf",
        preview="This is a test preview.",
    )

    # 2. List documents
    docs = history_service.list_documents()
    assert len(docs) == 1
    assert docs[0]["document_id"] == doc_id
    assert docs[0]["filename"] == "report.pdf"

    # 3. Save summary
    history_service.save_summary(
        document_id=doc_id,
        mode="extractive",
        length="medium",
        summary="This is an extractive summary.",
        word_count=50,
        character_count=300,
        compression_ratio=75.0,
        latency_seconds=0.45,
        analytics={"test": 123},
    )

    # 4. Get history detail
    history = history_service.get_document_history(doc_id)
    assert history is not None
    assert len(history["summaries"]) == 1
    assert history["summaries"][0]["mode"] == "extractive"
    assert history["summaries"][0]["analytics"] == {"test": 123}

    # 5. Delete document
    deleted = history_service.delete_document_history(doc_id)
    assert deleted is True
    assert history_service.get_document_history(doc_id) is None

