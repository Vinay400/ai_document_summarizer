# API Reference

The AI Document Summarization API is built with FastAPI. It provides endpoints for service health probing, document ingestion, extractive/abstractive/hybrid summarization, and ROUGE/BLEU evaluation.

Interactive OpenAPI documentation is also available at `/docs` when running the backend server.

---

## Base URL

`http://localhost:8000`

---

## Endpoints

### 1. Health Probe

`GET /api/health`

Checks backend status, Python environment, and Tesseract OCR availability.

#### Response `200 OK`

```json
{
  "status": "ok",
  "service": "AI Document Summarization API",
  "version": "0.1.0",
  "python_version": "3.11.9",
  "ocr": {
    "available": true,
    "tesseract_cmd": "C:\\Program Files\\Tesseract-OCR\\tesseract.exe",
    "language": "eng"
  }
}
```

---

### 2. Upload Document

`POST /api/upload`

Uploads a document (`.pdf`, `.docx`, or `.txt`), extracts its text, applies Tesseract OCR if scanned PDF pages are detected, cleans the prose, and stores it server-side.

#### Request

* **Content-Type**: `multipart/form-data`
* **Body**: `file` (binary document stream)

#### Response `200 OK`

```json
{
  "document_id": "a1b2c3d4e5f6...",
  "filename": "sample_report.pdf",
  "file_type": "pdf",
  "character_count": 12450,
  "word_count": 1980,
  "chunk_count": 14,
  "page_count": 5,
  "ocr_used": false,
  "extraction_method": "pdf-text-layer",
  "cleaning": {
    "raw_character_count": 12900,
    "removed_line_count": 12,
    "hyphenation_joins": 5
  },
  "preview": "This report summarizes key technical findings and project outcomes...",
  "warnings": []
}
```

#### Error Responses

* `400 Bad Request`: Empty file or unsupported extension.
* `413 Payload Too Large`: File size exceeds `MAX_FILE_SIZE_MB` (20 MB).

---

### 3. Summarize Document

`POST /api/summarize`

Generates a summary for an uploaded document using the specified strategy and target length.

#### Request Body

```json
{
  "document_id": "a1b2c3d4e5f6...",
  "mode": "extractive",
  "length": "medium"
}
```

* `mode`: `"extractive"` | `"abstractive"` | `"hybrid"` (default `"extractive"`)
* `length`: `"short"` | `"medium"` | `"long"` (default `"medium"`)

#### Response `200 OK`

```json
{
  "document_id": "a1b2c3d4e5f6...",
  "mode": "extractive",
  "length": "medium",
  "summary": "This report summarizes key technical findings... The system architecture demonstrates strong efficiency."
}
```

#### Error Responses

* `404 Not Found`: Unknown or expired `document_id`.
* `422 Unprocessable Entity`: Validation failure on `mode` or `length`.
* `501 Not Implemented`: Requested mode is invalid or unavailable.

---

### 4. Evaluate Summary

`POST /api/evaluate`

Summarizes an uploaded document and calculates ROUGE-1, ROUGE-2, ROUGE-L, and BLEU metrics against a user-provided reference summary.

#### Request Body

```json
{
  "document_id": "a1b2c3d4e5f6...",
  "reference": "This report highlights project outcomes and system performance results.",
  "mode": "hybrid",
  "length": "medium"
}
```

#### Response `200 OK`

```json
{
  "document_id": "a1b2c3d4e5f6...",
  "mode": "hybrid",
  "length": "medium",
  "summary": "This report highlights project outcomes and demonstrates system performance.",
  "reference": "This report highlights project outcomes and system performance results.",
  "metrics": {
    "rouge_1": 0.8235,
    "rouge_2": 0.6154,
    "rouge_l": 0.8235,
    "bleu": 48.21
  }
}
```

#### Error Responses

* `404 Not Found`: Unknown `document_id`.
* `422 Unprocessable Entity`: Missing reference text or invalid parameters.
