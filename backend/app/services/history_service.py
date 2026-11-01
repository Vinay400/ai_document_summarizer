"""
SQLite history service for persistent document and summary storage.

Persists documents, generated summaries, and evaluation runs so that user work
survives server restarts and can be revisited in a history panel.
Uses Python's standard `sqlite3` library for zero external dependencies.
"""

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

DB_PATH: Path = settings.upload_dir / "history.db"


def _get_connection() -> sqlite3.Connection:
    """Get a SQLite database connection with row factory configured."""
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize SQLite database tables if they do not exist."""
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                document_id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                character_count INTEGER NOT NULL,
                word_count INTEGER NOT NULL,
                page_count INTEGER,
                ocr_used INTEGER NOT NULL DEFAULT 0,
                extraction_method TEXT NOT NULL,
                preview TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT NOT NULL,
                mode TEXT NOT NULL,
                length TEXT NOT NULL,
                summary TEXT NOT NULL,
                word_count INTEGER NOT NULL,
                character_count INTEGER NOT NULL,
                compression_ratio REAL NOT NULL DEFAULT 0.0,
                latency_seconds REAL NOT NULL DEFAULT 0.0,
                analytics_json TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (document_id) REFERENCES documents(document_id) ON DELETE CASCADE
            )
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS evaluations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id TEXT NOT NULL,
                mode TEXT NOT NULL,
                length TEXT NOT NULL,
                rouge_1 REAL NOT NULL,
                rouge_2 REAL NOT NULL,
                rouge_l REAL NOT NULL,
                bleu REAL NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (document_id) REFERENCES documents(document_id) ON DELETE CASCADE
            )
            """
        )
        conn.commit()


def save_document(
    document_id: str,
    filename: str,
    file_type: str,
    character_count: int,
    word_count: int,
    page_count: int | None,
    ocr_used: bool,
    extraction_method: str,
    preview: str,
) -> None:
    """Save an uploaded document metadata entry into the history database."""
    init_db()
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO documents (
                document_id, filename, file_type, character_count, word_count,
                page_count, ocr_used, extraction_method, preview, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document_id,
                filename,
                file_type,
                character_count,
                word_count,
                page_count,
                1 if ocr_used else 0,
                extraction_method,
                preview[:300] if preview else "",
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()


def save_summary(
    document_id: str,
    mode: str,
    length: str,
    summary: str,
    word_count: int,
    character_count: int,
    compression_ratio: float = 0.0,
    latency_seconds: float = 0.0,
    analytics: dict[str, Any] | None = None,
) -> None:
    """Save a generated summary into the history database."""
    init_db()
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO summaries (
                document_id, mode, length, summary, word_count, character_count,
                compression_ratio, latency_seconds, analytics_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document_id,
                mode,
                length,
                summary,
                word_count,
                character_count,
                compression_ratio,
                latency_seconds,
                json.dumps(analytics) if analytics else None,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()


def save_evaluation(
    document_id: str,
    mode: str,
    length: str,
    metrics: dict[str, float],
) -> None:
    """Save an evaluation run into the history database."""
    init_db()
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO evaluations (
                document_id, mode, length, rouge_1, rouge_2, rouge_l, bleu, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                document_id,
                mode,
                length,
                metrics.get("rouge_1", 0.0),
                metrics.get("rouge_2", 0.0),
                metrics.get("rouge_l", 0.0),
                metrics.get("bleu", 0.0),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()


def list_documents(limit: int = 50) -> list[dict[str, Any]]:
    """List recent documents along with summary count."""
    init_db()
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT d.*, COUNT(s.id) as summary_count
            FROM documents d
            LEFT JOIN summaries s ON d.document_id = s.document_id
            GROUP BY d.document_id
            ORDER BY d.created_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def get_document_history(document_id: str) -> dict[str, Any] | None:
    """Get document details along with all its saved summaries and evaluations."""
    init_db()
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM documents WHERE document_id = ?", (document_id,))
        doc_row = cursor.fetchone()
        if not doc_row:
            return None

        cursor.execute(
            "SELECT * FROM summaries WHERE document_id = ? ORDER BY created_at DESC",
            (document_id,),
        )
        summary_rows = [dict(r) for r in cursor.fetchall()]
        for s in summary_rows:
            if s.get("analytics_json"):
                try:
                    s["analytics"] = json.loads(s["analytics_json"])
                except Exception:
                    s["analytics"] = None
            else:
                s["analytics"] = None

        cursor.execute(
            "SELECT * FROM evaluations WHERE document_id = ? ORDER BY created_at DESC",
            (document_id,),
        )
        eval_rows = [dict(r) for r in cursor.fetchall()]

        doc_dict = dict(doc_row)
        doc_dict["summaries"] = summary_rows
        doc_dict["evaluations"] = eval_rows
        return doc_dict


def delete_document_history(document_id: str) -> bool:
    """Delete a document and all related summaries from history."""
    init_db()
    with _get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM evaluations WHERE document_id = ?", (document_id,))
        cursor.execute("DELETE FROM summaries WHERE document_id = ?", (document_id,))
        cursor.execute("DELETE FROM documents WHERE document_id = ?", (document_id,))
        conn.commit()
        return cursor.rowcount > 0

