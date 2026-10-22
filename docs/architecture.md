# System Architecture & Design Decisions

This document details the architectural layout, component interactions, and key engineering decisions behind the AI Document Summarization platform.

---

## High-Level Architecture Diagram

```
                             ┌──────────────────────────────┐
                             │       React Frontend         │
                             │  Single-Page App (Vite 8)    │
                             └──────────────┬───────────────┘
                                            │
                                  axios HTTP Requests (CORS)
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 FastAPI Backend (:8000)                                │
│                                                                                        │
│   GET /api/health   │   POST /api/upload   │   POST /api/summarize   │  POST /api/evaluate │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                   Service Layer                                        │
│                                                                                        │
│   ┌────────────────────┐   ┌────────────────────┐   ┌────────────────────┐            │
│   │  document_service  │──►│    ocr_service     │──►│  cleaning_service  │            │
│   │ (PyMuPDF / docx)   │   │  (Tesseract OCR)   │   │(Reflow, Pagination)│            │
│   └─────────┬──────────┘   └────────────────────┘   └─────────┬──────────┘            │
│             │                                                 │                        │
│             └────────────────────────┬────────────────────────┘                        │
│                                      ▼                                                 │
│                            ┌────────────────────┐                                      │
│                            │  chunking_service  │                                      │
│                            │  (Punkt / Regex)   │                                      │
│                            └─────────┬──────────┘                                      │
│                                      │                                                 │
│              ┌───────────────────────┼───────────────────────┐                         │
│              ▼                       ▼                       ▼                         │
│    extractive_service       abstractive_service       hybrid_service               │
│    (MiniLM + TextRank)       (BART Map-Reduce)       (TextRank -> BART)                │
│              │                       │                       │                         │
│              └───────────────────────┼───────────────────────┘                         │
│                                      ▼                                                 │
│                           evaluation_service                                           │
│                         (ROUGE-1/2/L & BLEU)                                           │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## Key Design Decisions

### 1. Router vs Service Decoupling
* **`api/` layer**: Routers validate requests via Pydantic schemas, invoke business logic from `services/`, and format response models. Routers perform no heavy computation or algorithms directly.
* **`services/` layer**: Contains pure Python functions that are fully decoupled from HTTP concerns. Every service function can be imported and unit-tested in isolation without starting a FastAPI web server.

### 2. Server-Side Document Storage
* Documents uploaded via `POST /api/upload` are processed once (extracted, OCR'd if scanned, cleaned, and stored in `uploads/`).
* The API returns a unique `document_id` and metadata.
* Subsequent calls to `/api/summarize` or `/api/evaluate` pass `document_id` instead of re-uploading large PDF or DOCX files, preserving bandwidth and client memory.

### 3. Process-Level Singleton Models via `@lru_cache`
* Machine learning models (`sentence-transformers/all-MiniLM-L6-v2` and `facebook/bart-large-cnn`) are loaded lazily on first access and cached using `@lru_cache(maxsize=1)`.
* Heavy imports (`torch`, `transformers`, `sentence_transformers`) occur inside the cached getter functions, ensuring the FastAPI application starts up instantly without pulling PyTorch into memory until inference is requested.

### 4. Non-Blocking CPU Execution
* Model inference and TextRank graph algorithms are blocking CPU operations.
* Routers execute these operations using `await run_in_threadpool(func, ...)`, allowing FastAPI's async event loop to handle concurrent liveness probes (`/api/health`) without blocking.

### 5. Robust Sentence-Aware Chunking & Map-Reduce Strategy
* BART has a hard input context limit of 1024 tokens.
* `chunking_service` splits documents on sentence boundaries with overlapping seams to prevent mid-sentence fragments.
* `abstractive_service` uses a Map-Reduce strategy: chunking long documents, summarizing each chunk independently (Map), concatenating results, and performing a final condensation pass (Reduce) if necessary.
