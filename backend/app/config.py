"""Application settings, loaded from environment variables or `.env`."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# This file is <root>/backend/app/config.py
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _resolve(value: str) -> Path:
    """Anchor a relative path to the project root.

    Without this, `UPLOAD_DIR=uploads` would mean different directories
    depending on where uvicorn was started from.
    """
    path = Path(value)
    return path if path.is_absolute() else PROJECT_ROOT / path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ---- Application ----
    APP_NAME: str = "AI Document Summarization API"
    APP_VERSION: str = "0.1.0"

    # ---- Server ----
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000

    # Comma-separated, not a list: pydantic-settings would try to JSON-decode a
    # list field before any validator runs, and "http://a,http://b" is not JSON.
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    # ---- Uploads ----
    MAX_FILE_SIZE_MB: int = 20
    ALLOWED_EXTENSIONS: str = ".pdf,.docx,.txt"
    UPLOAD_DIR: str = "uploads"
    OUTPUT_DIR: str = "outputs"

    # ---- OCR (Phase 3) ----
    OCR_LANGUAGE: str = "eng"
    OCR_DPI: int = 200
    # A PDF page yielding fewer characters than this is treated as an image.
    OCR_MIN_CHARS_PER_PAGE: int = 80
    TESSERACT_CMD: str | None = None

    # ---- Chunking (Phase 4) ----
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 100

    # ---- Cleaning (Phase 4) ----
    CLEAN_STRIP_HEADERS: bool = True
    # A short line repeating at least this many times is treated as a running
    # header or footer and removed. Higher = more conservative.
    HEADER_MIN_REPEATS: int = 3
    # Only lines this short are ever considered headers; a repeated full
    # sentence is content, however often it recurs.
    HEADER_MAX_CHARS: int = 120

    # ---- Models (Phases 5-7) ----
    EXTRACTIVE_MODEL: str = "sentence-transformers/all-MiniLM-L6-v2"
    ABSTRACTIVE_MODEL: str = "facebook/bart-large-cnn"
    ABSTRACTIVE_DEVICE: str = "cpu"

    # ---- Derived values ----
    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def allowed_extensions(self) -> set[str]:
        return {e.strip().lower() for e in self.ALLOWED_EXTENSIONS.split(",") if e.strip()}

    @property
    def max_file_size_bytes(self) -> int:
        return self.MAX_FILE_SIZE_MB * 1024 * 1024

    @property
    def upload_dir(self) -> Path:
        return _resolve(self.UPLOAD_DIR)

    @property
    def output_dir(self) -> Path:
        return _resolve(self.OUTPUT_DIR)

    def ensure_directories(self) -> None:
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
