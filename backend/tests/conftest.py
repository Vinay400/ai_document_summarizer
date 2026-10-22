"""Shared pytest fixtures.

The sample documents are produced by `python tests/make_fixtures.py`. If they
are absent the dependent tests skip with an instruction, rather than failing
with a confusing FileNotFoundError.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture(scope="session")
def fixtures_dir() -> Path:
    """Directory holding the generated sample PDF / DOCX / TXT files."""
    if not FIXTURES_DIR.is_dir() or not any(FIXTURES_DIR.iterdir()):
        pytest.skip("No test fixtures - run: python tests/make_fixtures.py")
    return FIXTURES_DIR


@pytest.fixture(scope="session")
def tesseract_available() -> bool:
    """Whether the Tesseract binary can actually be used on this machine.

    Tesseract is an external program, not something `pip install -r
    requirements.txt` can provide, so tests that need real OCR are skipped when
    it is missing. The same tests run and pass on a machine that has it.
    """
    from app.services import ocr_service

    return ocr_service.availability()[0]


@pytest.fixture
def client(tmp_path, monkeypatch):
    """An API client whose document store is a throwaway directory.

    `upload_dir` is a derived property, so redirecting UPLOAD_DIR redirects both
    the temporary upload file and the stored text.
    """
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    with TestClient(app) as test_client:
        yield test_client
