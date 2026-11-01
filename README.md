# AI Document Summarization

**An Intelligent Extractive, Abstractive, and Hybrid Summarization Platform for Long-Form Documents with RAG Q&A, Hallucination Guardrails, and Readability Analytics**

A production-grade, full-stack application that ingests PDF, DOCX, and TXT documents (with automatic OCR for scanned pages), cleans and chunks the text, and produces summaries using three distinct strategies. Features interactive Retrieval-Augmented Generation (RAG) Q&A, semantic hallucination detection, Flesch-Kincaid readability scoring, persistent SQLite history, and ROUGE/BLEU evaluation.

📘 **[Plain-English Project Overview & Viva Guide](PROJECT_CONCEPTS.md)**

---

## Key Features

1. **Three Complementary Summarization Strategies**:
   * **Extractive**: Dense sentence embeddings (`all-MiniLM-L6-v2`) + Cosine Similarity Graph + TextRank (PageRank). Zero hallucination guarantee.
   * **Abstractive**: Sequence-to-sequence Transformer (`facebook/bart-large-cnn`) with sentence-aware Map-Reduce chunking for documents exceeding token limits.
   * **Hybrid**: Two-stage pipeline where TextRank filters out low-information sentences before BART condenses the core concepts into fluent prose.
   * **3-Way Comparison Matrix**: Run all three strategies simultaneously to compare word counts, compression ratios, latency, and outputs side-by-side.

2. **Explainable AI & Factuality / Hallucination Guardrail**:
   * Evaluates each generated summary sentence against source document sentences using semantic embeddings.
   * Computes an overall **Factuality Confidence %** and assigns a **Hallucination Risk Level** (Low / Medium / High).
   * **Interactive Source Alignment**: Maps and visualizes which source sentence served as the factual anchor for each generated statement.

3. **Readability & Efficiency Analytics**:
   * Calculates **Flesch Reading Ease** ($0\text{--}100$) and **Flesch-Kincaid Grade Level** before and after summarization.
   * Quantifies real-world efficiency by reporting exact **Reading Time Saved (seconds and %)**.
   * Extracts top **Keyphrases and Topical Hashtags** from the document.

4. **Interactive Document Q&A (RAG Assistant)**:
   * Ask free-form questions about uploaded documents.
   * Semantic passage retrieval matches question embeddings against document passages and synthesizes grounded answers with verifiable source citations.

5. **Persistent Document & Summary History**:
   * Built-in zero-dependency SQLite store (`uploads/history.db`) automatically archives documents, generated summaries, analytics, and ROUGE/BLEU scores.
   * Slide-out History Drawer allows reloading past documents and summaries instantly.

6. **Executive Summary Export**:
   * One-click download of a publication-ready **Executive Summary Brief** (formatted HTML/PDF or Markdown) complete with key topics, summary text, and analytical metrics.

7. **Production Document Pipeline & OCR**:
   * Ingests native PDF, DOCX (paragraphs and tables), and TXT files.
   * Automatically detects scanned image-only PDF pages and routes them to Tesseract OCR.
   * Automated text cleaning: de-hyphenation across line breaks, header/footer removal, and paragraph reflow.

---

## Project Status

| Phase | Scope | Status |
|---|---|---|
| 1 | Project setup — FastAPI, Vite/React/Tailwind, CORS, health endpoint | ✅ Complete |
| 2 | Document ingestion — PDF, DOCX, TXT, validation, metadata | ✅ Complete |
| 3 | OCR — scanned-PDF detection and Tesseract fallback | ✅ Complete |
| 4 | Preprocessing — cleaning, sentence segmentation, chunking | ✅ Complete |
| 5 | Extractive summarization — embeddings + TextRank | ✅ Complete |
| 6 | Abstractive summarization — transformer + map-reduce | ✅ Complete |
| 7 | Hybrid summarization — TextRank filter $\rightarrow$ BART condensation | ✅ Complete |
| 8 | Evaluation — ROUGE-1/2/L, BLEU against reference | ✅ Complete |
| 9 | Frontend — modern UI, comparison matrix, text-to-speech audio | ✅ Complete |
| 10 | Testing & Quality Assurance — 97 automated tests across modules | ✅ Complete |
| 11 | Analytics & Explainability — Readability, Keyphrases, Hallucination Guardrail | ✅ Complete |
| 12 | Interactive RAG Assistant — Retrieval-augmented document Q&A with citations | ✅ Complete |
| 13 | Persistence & History — SQLite store for documents and summaries | ✅ Complete |
| 14 | Deployment & Packaging — 1-Click Launchers and Docker Compose orchestration | ✅ Complete |

---

## Architecture

```
React Frontend (Vite, :5173)
       │  axios HTTP JSON (CORS enabled)
       ▼
FastAPI Backend (:8000) /api/{upload, summarize, evaluate, chat, history, export}
       │
       ├─► api/             Request validation, router dispatch, response schemas
       │
       ├─► services/
       │     document_service ──► PyMuPDF | python-docx | plain text read
       │           ├─► ocr_service         ──► Tesseract OCR (scanned pages only)
       │           ├─► cleaning_service    ──► Normalise, de-hyphenate, strip headers/footers
       │           └─► chunking_service    ──► Sentence-aware, overlapping chunks
       │
       │     ┌─────────────────────┼─────────────────────┐
       │     ▼                     ▼                     ▼
       │ extractive_service   abstractive_service   hybrid_service
       │ MiniLM embeddings    BART Map-Reduce       TextRank filter ──► BART condenses
       │ Cosine TextRank      for long docs
       │     └─────────────────────┼─────────────────────┘
       │                           ▼
       │     analytics_service   ──► Flesch Readability, Keyphrases, Hallucination Check
       │     qa_service          ──► Semantic passage retrieval & RAG Q&A
       │     evaluation_service  ──► ROUGE-1/2/L & BLEU metrics
       │     history_service     ──► SQLite persistent archive (history.db)
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 19, Vite 8, Tailwind CSS v4, Axios, Web Speech API |
| **Backend** | Python 3.11, FastAPI, Uvicorn, Pydantic v2 |
| **Database** | SQLite3 (built-in persistent storage) |
| **Extraction & OCR** | PyMuPDF (fitz), python-docx, Tesseract OCR, Pillow |
| **ML / NLP** | `sentence-transformers` (`all-MiniLM-L6-v2`), `transformers` (`facebook/bart-large-cnn`), PyTorch, NetworkX, Scikit-learn, NLTK |
| **Evaluation** | `rouge-score`, `sacrebleu` |
| **Deployment** | Docker, Docker Compose, Nginx |
| **Testing** | pytest, httpx |

---

## Folder Structure

```
ai-document-summarization/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app factory, CORS, routers
│   │   ├── config.py            # Settings from environment / .env
│   │   ├── api/                 # Endpoints (upload, summarize, evaluate, chat, history)
│   │   ├── services/            # Algorithms (extractive, abstractive, hybrid, analytics, qa, history)
│   │   ├── models/schemas.py    # Pydantic request/response contracts
│   │   └── utils/               # Text and file helper utilities
│   ├── tests/                   # Automated unit & integration tests
│   ├── Dockerfile               # Container definition for backend
│   └── requirements.txt         # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/          # React components (SummaryDisplay, DocumentChat, HistoryDrawer, etc.)
│   │   ├── pages/Home.jsx       # Main single-page application workflow
│   │   └── services/api.js      # Backend API client wrapper
│   ├── Dockerfile               # Multi-stage Node/Nginx container definition
│   ├── nginx.conf               # Nginx reverse proxy configuration
│   └── package.json
├── docs/                        # Architecture, API, and methodology documentation
├── uploads/                     # Server-side document storage & history.db (gitignored)
├── outputs/                     # Output directory (gitignored)
├── docker-compose.yml           # One-click multi-container deployment
├── run_backend.bat / .ps1       # 1-Click launcher for backend on Windows
├── run_frontend.bat / .ps1      # 1-Click launcher for frontend on Windows
├── PROJECT_CONCEPTS.md          # Plain-English viva questions & concept guide
└── README.md
```

---

## Quick Start (How to Run)

### Method 1: 1-Click Windows Launchers (Recommended)

Simply double-click the starter scripts in the project root:

1. **Backend**: Double-click `run_backend.bat` (or execute `.\run_backend.ps1` in PowerShell).
2. **Frontend**: Double-click `run_frontend.bat` (or execute `.\run_frontend.ps1` in PowerShell).

---

### Method 2: Manual Terminal Commands

#### Terminal 1 — Backend (FastAPI)

```powershell
cd backend
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

> **Note for Windows PowerShell:** Use a semicolon (`;`) rather than `&&` if running as a single line:  
> `cd backend; .\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000`

* **Backend URL**: [http://localhost:8000](http://localhost:8000)
* **Interactive API Docs (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)

#### Terminal 2 — Frontend (React / Vite)

```powershell
cd frontend
npm run dev
```

* **Frontend Web UI**: [http://localhost:5173](http://localhost:5173)

---

### Method 3: Run with Docker Compose

If you have Docker Desktop installed, build and launch the entire platform with one command:

```bash
docker compose up --build
```

---

## API Endpoints Reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Service liveness probe, runtime versions, and OCR status |
| `POST` | `/api/upload` | Upload PDF/DOCX/TXT; extracts, cleans, OCRs if needed, returns `document_id` |
| `POST` | `/api/summarize` | Generate single-mode summary with readability and factuality analytics |
| `POST` | `/api/summarize/compare` | Generate summaries for all 3 strategies simultaneously for side-by-side comparison |
| `POST` | `/api/evaluate` | Compute ROUGE-1/2/L and BLEU scores against a reference summary |
| `POST` | `/api/evaluate/compare` | Evaluate all 3 modes against a reference summary |
| `POST` | `/api/chat` | Interactive RAG Q&A: answer questions with document source citations |
| `GET` | `/api/history` | List all historical documents, word counts, and summary statistics |
| `GET` | `/api/history/{id}` | Retrieve document details, all saved summaries, and evaluation runs |
| `DELETE`| `/api/history/{id}` | Delete a document and its associated records from SQLite history |
| `POST` | `/api/export/brief` | Export a formatted Executive Summary Report (HTML & Markdown) |

---

## Running the Automated Test Suite

The test suite covers document extraction, OCR orchestration, cleaning heuristics, sentence segmentation, chunking, extractive/abstractive pipelines, RAG Q&A, analytics, and SQLite persistence:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests -v
```

---

## License & Academic Disclaimer

Developed as an **MCA Major Project**. Built using open-source libraries and pretrained models from Hugging Face and Sentence-Transformers.
