# Backend — AI Document Summarization

FastAPI service providing document extraction, OCR, chunking, three
summarization strategies and ROUGE/BLEU evaluation.

## Setup

```bash
cd backend

# Virtual environment (Python 3.11 recommended — best wheel coverage for torch)
py -3.11 -m venv .venv

# Activate
.venv/Scripts/activate        # Windows (Git Bash / cmd)
# source .venv/bin/activate   # macOS / Linux

pip install -r requirements.txt

# NLTK ships the library but not its models. Without this the chunker falls
# back to a regex sentence splitter (correct, just less robust on hard prose).
.venv/Scripts/python.exe -c "import nltk; nltk.download('punkt_tab')"
```

## Run

```bash
# from the backend/ directory
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
```

* API docs: http://localhost:8000/docs
* Health:   http://localhost:8000/api/health

## Test

```bash
# once, to generate tests/fixtures/*.pdf|docx|txt
.venv/Scripts/python.exe tests/make_fixtures.py

.venv/Scripts/python.exe -m pytest tests -v
```

`pytest.ini` puts `backend/` on `sys.path` so the tests can `import app` without
installing the package.

Tesseract is an external program that `pip install` cannot provide, so the two
tests asserting real OCR quality skip when it is absent. Everything else —
including the OCR orchestration, with recognition stubbed — runs regardless.

## Layout

| Path | Responsibility |
|---|---|
| `app/main.py` | App factory, CORS, error handlers, router registration |
| `app/config.py` | All settings, read from environment / `.env` |
| `app/api/` | HTTP endpoints — validation and response shaping only |
| `app/services/` | Business logic; framework-agnostic and unit-testable |
| `app/models/schemas.py` | Pydantic request/response contracts |
| `app/utils/` | Shared text and file helpers |
| `tests/` | pytest suite |

The `api` / `services` split is deliberate: routers contain no algorithms, so
every summarization and preprocessing function can be tested directly without
starting a server.
