# AI Document Summarization

**An Intelligent Extractive, Abstractive, and Hybrid Summarization Platform for Long-Form Documents**

MCA Major Project — a full-stack application that ingests PDF, DOCX and TXT
documents, cleans and chunks the text, and produces summaries using three
complementary strategies, with ROUGE and BLEU evaluation against a reference
summary.

📖 **[Plain-English Project Overview & Viva Guide](PROJECT_CONCEPTS.md)**


---

## Status

The project is built in phases. Current progress:

| Phase | Scope | Status |
|---|---|---|
| 1 | Project setup — FastAPI, Vite/React/Tailwind, CORS, health endpoint | ✅ Complete |
| 2 | Document ingestion — PDF, DOCX, TXT, validation, metadata | ✅ Complete |
| 3 | OCR — scanned-PDF detection and Tesseract fallback | ✅ Complete |
| 4 | Preprocessing — cleaning, sentence segmentation, chunking | ✅ Complete |
| 5 | Extractive summarization — embeddings + TextRank | ✅ Complete |
| 6 | Abstractive summarization — transformer + map-reduce | ✅ Complete |
| 7 | Hybrid summarization | ✅ Complete |
| 8 | Evaluation — ROUGE-1/2/L, BLEU | ✅ Complete |
| 9 | Frontend — upload, selectors, progress, summary, evaluation | ✅ Complete |
| 10 | Testing and error handling | ✅ Complete |
| 11 | Documentation | ✅ Complete |
| 12 | Docker / deployment (only after everything works locally) | ⏳ |

---

## Architecture

```
React (Vite, :5173)
      │  axios, JSON — cross-origin, so CORS is configured on the API
      ▼
FastAPI (:8000) /api/{upload,summarize,evaluate,health}
      │
      ├── api/          validate request → call service → shape response
      │
      └── services/
            document_service ──► PyMuPDF | python-docx | plain read
                  ├── ocr_service      ► Tesseract (scanned pages only)
                  ├── cleaning_service ► normalise, de-hyphenate, strip headers/footers
                  └── chunking_service ► sentence-aware, overlapping chunks
                                             │
              ┌──────────────────────────────┼──────────────────────────────┐
              ▼                              ▼                              ▼
      extractive_service            abstractive_service            hybrid_service
      MiniLM embeddings →           BART; map-reduce over          TextRank filter →
      cosine similarity →           chunks for long docs           BART condenses
      TextRank → top-k sentences
              └──────────────────────────────┼──────────────────────────────┘
                                             ▼
                                  evaluation_service — ROUGE-1/2/L, BLEU
```

### Design decisions

* **`api/` vs `services/` separation.** Routers hold no algorithms. Every
  summarizer and preprocessor is a plain function that can be unit-tested
  without an HTTP server.
* **Server-side document store.** `/api/upload` extracts text once and returns
  only a `document_id` plus metadata; `/api/summarize` sends the ID, never the
  full text. The client never re-uploads a 20 MB PDF to switch modes.
* **Models are process-level singletons.** The Sentence-Transformers and BART
  models are loaded once via a cached registry, not per request — reloading BART
  per request would add ~10 s to every call.
* **Chunking exists because of model limits.** BART accepts 1024 tokens; longer
  documents must be split, summarized chunk-by-chunk (map) and then condensed
  (reduce).

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 19, Vite 8, Tailwind CSS v4, axios |
| Backend | Python 3.11, FastAPI, Uvicorn, Pydantic v2 |
| Extraction | PyMuPDF (fitz), python-docx |
| OCR | Tesseract via pytesseract, Pillow |
| ML / NLP | sentence-transformers, transformers (BART), torch, networkx, scikit-learn, NLTK |
| Evaluation | rouge-score, sacreBLEU |
| Data | pandas, NumPy |
| Testing | pytest, httpx |

---

## Folder structure

```
ai-document-summarization/
├── backend/
│   ├── app/
│   │   ├── main.py            # app factory, CORS, error handlers
│   │   ├── config.py          # settings from env / .env
│   │   ├── api/               # HTTP endpoints
│   │   ├── services/          # business logic
│   │   ├── models/schemas.py  # request / response contracts
│   │   └── utils/             # text and file helpers
│   ├── tests/
│   ├── requirements.txt
│   └── README.md
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/Home.jsx
│   │   ├── services/api.js
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── package.json
│   └── README.md
├── docs/                      # architecture, api, methodology, evaluation
├── uploads/                   # transient uploaded documents (gitignored)
├── outputs/                   # generated summaries (gitignored)
├── .env.example
└── README.md
```

---

## Installation

### Prerequisites

* **Python 3.11** (recommended for ML wheel availability) — `py -3.11 --version`
* **Node.js 20.19+ or 22.12+** — `node --version`
* **Tesseract OCR** — required from Phase 3 onwards.

#### Installing Tesseract on Windows

1. Download the installer from
   <https://github.com/UB-Mannheim/tesseract/wiki> (e.g. `tesseract-ocr-w64-setup-5.x.exe`).
2. Install to the default location: `C:\Program Files\Tesseract-OCR`.
3. Either add that folder to `PATH`, or set `TESSERACT_CMD` in `.env`:
   ```
   TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
   ```
4. Verify: `tesseract --version`

*Linux:* `sudo apt install tesseract-ocr` · *macOS:* `brew install tesseract`

> The Windows installer (including the winget package `UB-Mannheim.TesseractOCR`)
> does **not** reliably add Tesseract to `PATH`. If `tesseract --version` works in
> a terminal but the app still reports `ocr.available: false`, set `TESSERACT_CMD`
> in `.env` — that is the deterministic fix, and it is what this project uses.

#### OCR is optional, but needed for scanned PDFs

Tesseract is an external program — `pip install pytesseract` installs only the
Python wrapper, so the phase 3 code runs either way:

* **Without it**, digital PDFs, DOCX and TXT work normally. A scanned upload is
  rejected with a message naming the fix, and `GET /api/health` reports
  `ocr.available: false` so the front-end can warn before an upload is attempted.
* **With it**, OCR runs *only* on pages whose text layer is empty (fewer than
  `OCR_MIN_CHARS_PER_PAGE` characters) — never on a page that already has text,
  so ordinary PDFs pay nothing for this. Partly scanned documents keep their
  digital pages and have the image pages filled in, and each extraction reports
  which route it took via `extraction_method` and `warnings`.

OCR runs at `OCR_DPI` (default 200); the Tesseract default of 72 DPI misreads
small text. `OCR_LANGUAGE` selects the language pack.

### What cleaning does

Extraction returns what the file literally contains — a PDF page is a grid of
lines — so `cleaning_service` turns that back into prose before anything is
stored:

| Step | Effect |
|---|---|
| Character normalisation | Ligatures, curly quotes, en/em dashes and non-breaking spaces folded to ASCII, so a summary matches a reference summary written with plain characters |
| Page numbers | `Page 12`, `12 of 30`, `- 12 -` removed; a *lone* bare number is kept, since it is more likely a year or a table cell than a page number |
| Headers / footers | A short line repeating `HEADER_MIN_REPEATS` times is boilerplate and removed |
| De-hyphenation | `summa-` ⏎ `rization` → `summarization`; a hyphen before a capital is kept, as in `State-Of-The-Art` |
| Reflow | Wrapped lines rejoin into paragraphs; blank lines stay as paragraph breaks |

It is deliberately conservative — deleting content is a worse failure than
keeping a stray footer — so a repeated *sentence* is never treated as a header,
however often the document repeats it. `POST /api/upload` reports what changed
under `cleaning`, and `GET /api/health` is unaffected.

Chunking then splits the cleaned text for models with a token limit. Chunks are
sentence-aligned and overlap so a fact spanning a boundary is not lost. The
overlap always includes the sentence at the boundary, even if that exceeds
`CHUNK_OVERLAP` slightly: a sentence stopping short of the seam would duplicate
text already fully contained in the previous chunk without bridging anything.

### Environment

```bash
cp .env.example .env                    # root: backend settings
cp frontend/.env.example frontend/.env  # frontend: API base URL
```

### Backend

```bash
cd backend
py -3.11 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt

# One-off: NLTK's sentence-tokenizer data. `pip install nltk` ships the library
# but not the models, so this download is a separate step.
.venv/Scripts/python.exe -c "import nltk; nltk.download('punkt_tab')"
```

**NLTK data is optional.** Without it the pipeline falls back to a built-in
regex sentence splitter that handles abbreviations and decimals. Punkt is better
on complex prose, so the download is worth doing. `GET /api/health` does not
report this, but `chunking_service.sentence_tokenizer()` returns `'nltk-punkt'`
or `'regex'`.

### Frontend

```bash
cd frontend
npm install
```

---

## Running the project

Two terminals.

**Terminal 1 — backend**
```bash
cd backend
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000
```

**Terminal 2 — frontend**
```bash
cd frontend
npm run dev
```

Open <http://localhost:5173>. The home page probes `GET /api/health` and shows
a green "Backend connected" panel when the two halves are talking.

> **Heads-up:** the first run downloads models — ~90 MB for `all-MiniLM-L6-v2`
> and ~1.6 GB for `facebook/bart-large-cnn`. They are cached afterwards.

---

## API endpoints

| Method | Path | Purpose | Phase |
|---|---|---|---|
| `GET` | `/api/health` | Liveness probe, runtime info, OCR availability | 1, 3 |
| `POST` | `/api/upload` | Upload PDF/DOCX/TXT, extract, OCR if needed, clean | 2–4 |
| `POST` | `/api/summarize` | Generate a summary for an uploaded document | 5–7 |
| `POST` | `/api/evaluate` | ROUGE-1/2/L and BLEU against a reference | 8 |

`POST /api/upload` returns metadata only — never the text. Alongside the counts
and `extraction_method` it reports `ocr_used`, any `warnings` (image-only pages,
OCR recognition caveats), the `cleaning` counts, and `chunk_count`: how many
chunks the document would be split into at the current `CHUNK_SIZE`.

Full reference: [`docs/api.md`](docs/api.md) (Phase 11).

---

## Testing

```bash
cd backend
.venv/Scripts/python.exe tests/make_fixtures.py   # once: generates tests/fixtures/
.venv/Scripts/python.exe -m pytest tests -v
```

The suite covers extraction for all four input kinds, cleaning, sentence
segmentation, chunking, the OCR fallback and the upload endpoint.

Two techniques keep it portable, since both external pieces are optional. OCR
orchestration (which pages are rendered, how results are merged, what happens
when Tesseract dies mid-document) is tested with the recognition step stubbed,
so it runs on every machine; only the two tests asserting real recognition
quality skip without Tesseract. In the same way, punkt's split behaviour is
tested by calling the repair function on synthetic output, so those assertions
hold whether or not the NLTK data is installed.

---

## Limitations

* Abstractive summaries can hallucinate facts not present in the source; the
  hybrid mode exists specifically to constrain generation to extractively
  selected content.
* OCR accuracy depends on scan quality, and a summary of a scanned document
  inherits Tesseract's recognition errors. Extracted text is not corrected or
  spell-checked.
* Cleaning removes only *exactly* repeated headers and footers. A footer whose
  text changes on every page (`Report 2024 - page 3`) survives, because masking
  the digits to catch it would also delete genuinely numbered short lines such
  as a run of table captions. Removing a real line is worse than keeping a
  footer.
* Sentence segmentation is heuristic. It handles the common abbreviations,
  initials, decimals and dotted forms, but an unusual abbreviation can still be
  mistaken for a sentence end — and extractive summarization quotes sentences
  verbatim, so a bad split shows up directly in the output.
* ROUGE and BLEU are **reference-based** metrics — they cannot be computed
  without a reference summary, so evaluation is optional and user-supplied.
* Transformer inference runs on CPU by default; long documents take minutes.

---

## Future scope

* Summary history backed by SQLite/PostgreSQL
* GPU inference and quantized models
* Multi-document and query-focused summarization
* Multilingual OCR and summarization
* Export to DOCX/PDF alongside TXT
#   a i _ d o c u m e n t _ s u m m a r i z e r  
 