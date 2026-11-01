# AI Document Summarization ΓÇö Project Concepts & Plain-English Guide

> **MCA Minor Project Explanation & Viva Guide**  
> This document explains what this application does, how its algorithms work, and key concepts in plain, non-jargon language suitable for project reports and viva examinations.

---

## 1. What Does This Project Actually Do?

This application takes long documents (**PDF**, **DOCX**, or **TXT**) and automatically generates short, accurate summaries using three different Artificial Intelligence approaches:

1. **Extractive Summarization**: Picks and quotes the most important sentences directly from the document without changing any words.
2. **Abstractive Summarization**: Reads the document and rewrites the key ideas in new, fluent sentences (like a human summarizer).
3. **Hybrid Summarization**: First filters out unnecessary sentences using Extractive scoring, then rewrites the remaining key sentences using Abstractive AI.

Finally, if you provide a human-written reference summary, the application calculates mathematical quality scores (**ROUGE** and **BLEU**) to measure how good the AI-generated summary is.

---

## 2. The 5-Step Pipeline (End-to-End Flow)

```
ΓöîΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÉ      ΓöîΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÉ      ΓöîΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÉ
Γöé  1. Ingestion   Γöé ΓöÇΓöÇΓöÇΓû║ Γöé  2. Cleaning    Γöé ΓöÇΓöÇΓöÇΓû║ Γöé   3. Chunking   Γöé
Γöé  Extract / OCR  Γöé      Γöé Reflow & Strip  Γöé      Γöé Token Overlap   Γöé
ΓööΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÿ      ΓööΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÿ      ΓööΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓö¼ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÿ
                                                           Γöé
ΓöîΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÉ      ΓöîΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÉ               Γöé
Γöé  5. Evaluation  Γöé ΓùäΓöÇΓöÇΓöÇ Γöé 4. Summarize    Γöé ΓùäΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÿ
Γöé  ROUGE & BLEU   Γöé      Γöé Ext/Abs/Hybrid  Γöé
ΓööΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÿ      ΓööΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÿ
```

---

## 3. Core Concepts Explained Simply

### Concept 1: Text Extraction & OCR Fallback
* **Digital PDF / DOCX / TXT**: Digital files already contain text characters inside their code structure. We extract this directly using libraries (`PyMuPDF` for PDF, `python-docx` for DOCX).
* **Scanned PDF (Image PDF)**: A scanned document is just a picture of paper ΓÇö it has no text characters inside.
* **Optical Character Recognition (OCR)**: When the system detects an image-only PDF page, it automatically passes that page to **Tesseract OCR**, which reads the visual letters in the image and converts them into editable text characters.

---

### Concept 2: Text Preprocessing & Cleaning
Raw extracted text from PDFs is often messy (line breaks in the middle of sentences, repeated header/footer lines, page numbers like `Page 12 of 50`).

Before summarization, `cleaning_service` performs 4 clean-ups:
1. **Header/Footer Removal**: Detects short lines that repeat across multiple pages and strips them out.
2. **De-hyphenation**: Rejoins broken words (e.g., `summa-` ΓÅÄ `rization` becomes `summarization`).
3. **Paragraph Reflow**: Merges single line-wraps into continuous prose paragraphs.
4. **Character Normalization**: Replaces fancy quotes or ligatures with standard characters.

---

### Concept 3: Sentence Segmentation & Chunking
* **The Token Limit Problem**: Language models like **BART** have a hard limit of **1024 tokens** (~750 words). They cannot read a 50-page PDF in a single pass.
* **Sentence-Aware Chunking**: We split long documents into smaller slices (chunks). Slices are strictly cut at sentence boundariesΓÇönever in the middle of a sentenceΓÇöso the AI doesn't receive cut-off fragments.
* **Overlapping Seams**: Consecutive chunks share 1-2 overlapping sentences at their boundary so that important facts spanning across two chunks aren't lost.

---

### Concept 4: The Three Summarization Strategies

#### A. Extractive Summarization (Embeddings + TextRank)
* **How it works**:
  1. Each sentence is converted into a numerical vector representation (embedding) using the `all-MiniLM-L6-v2` Sentence Transformer model.
  2. The system compares every sentence against every other sentence using **Cosine Similarity**.
  3. It builds a network graph where sentences are nodes and edge weights are similarity scores.
  4. It runs **PageRank** (TextRank) on the graph. A sentence scores high if it is semantically similar to *many other sentences* in the document.
  5. Top-ranked sentences are selected and placed back in their original document order.
* **Key Trait**: **Zero Hallucination** ΓÇö quotes exact words from the source. Cannot invent false facts.

#### B. Abstractive Summarization (BART + Map-Reduce)
* **How it works**: Uses `facebook/bart-large-cnn`, a Sequence-to-Sequence (Seq2Seq) Transformer neural network.
* **Map-Reduce for Long Texts**:
  * **Map**: Splits long document into overlapping chunks and generates a partial summary for each chunk.
  * **Reduce**: Combines all partial summaries together and condenses them into one final summary.
* **Key Trait**: **Fluent Rewriting** ΓÇö creates new, natural sentences that synthesize complex concepts.

#### C. Hybrid Summarization (TextRank Filter $\rightarrow$ BART Condensation)
* **How it works**:
  1. Step 1: Uses TextRank to identify and extract the top 50% most important sentences in the document.
  2. Step 2: Feeds only those top sentences into BART to generate a condensed abstractive summary.
* **Key Trait**: **Best of Both Worlds** ΓÇö keeps BART focused only on factual, core sentences, greatly reducing hallucination risk while maintaining smooth, human-like readability.

---

### Concept 5: Evaluation Metrics (ROUGE & BLEU)

When evaluating AI summaries against a human reference summary:

| Metric | Full Form | What It Measures | Scale |
|---|---|---|---|
| **ROUGE-1** | Recall-Oriented Understudy for Gisting Evaluation | Single word (unigram) overlap between AI summary and human reference. | 0.0 ΓÇô 1.0 (Higher is better) |
| **ROUGE-2** | Bigram Overlap | Two-word sequence overlap; measures local phrase accuracy. | 0.0 ΓÇô 1.0 (Higher is better) |
| **ROUGE-L** | Longest Common Subsequence | Longest matching sequence of words; measures sentence structure similarity. | 0.0 ΓÇô 1.0 (Higher is better) |
| **BLEU** | Bilingual Evaluation Understudy | N-gram precision with brevity penalty; measures translation/generation quality. | 0 ΓÇô 100 (Higher is better) |

---

## 4. Key Technologies Used

| Layer | Technology | Why It Was Chosen |
|---|---|---|
| **Backend** | Python 3.11 + FastAPI | Fast async Python framework with automatic OpenAPI docs and Pydantic validation. |
| **Frontend** | React 19 + Vite + Tailwind CSS v4 | Modern single-page UI with state-machine reactive rendering and utility styling. |
| **Extraction** | PyMuPDF (fitz) & python-docx | High-speed PDF text extraction and DOCX structure parsing. |
| **OCR** | Tesseract OCR + pytesseract | Fallback engine to extract text from scanned image PDFs. |
| **Embeddings** | Sentence-Transformers (`all-MiniLM-L6-v2`) | Lightweight 90 MB model producing 384-dimensional dense semantic vectors. |
| **Abstractive Model** | Transformers (`facebook/bart-large-cnn`) | State-of-the-art seq2seq model pretrained specifically for document summarization. |
| **Evaluation** | `rouge-score` & `sacrebleu` | Industry standard Python evaluation benchmark packages. |

---

## 5. Viva / Presentation Q&A Cheat-Sheet

**Q1: Why did you implement three different summarization methods?**  
*Answer*: Because each method has distinct trade-offs. Extractive summarization guarantees 100% factual fidelity (no hallucination) but can sound disjointed. Abstractive summarization writes fluent, human-like summaries but risks hallucinating ungrounded details. Hybrid summarization combines TextRank filtering with BART condensation to achieve high factual grounding *and* linguistic fluency.

**Q2: How does the system handle long documents that exceed model limits?**  
*Answer*: BART has a 1024 token context window limit. We implement sentence-aware chunking with overlap to split the document, apply a Map step to summarize individual chunks, and a Reduce step to condense the combined chunk summaries into a cohesive final output.

**Q3: What is the difference between ROUGE and BLEU?**  
*Answer*: ROUGE is recall-oriented and checks how much of the reference summary content was captured by the AI summary. BLEU is precision-oriented and checks how much of the AI summary matches the reference, penalized if the generated text is overly brief.

**Q4: How does the system ensure high backend performance?**  
*Answer*: 
1. Machine learning models are loaded lazily as singletons using `@lru_cache(maxsize=1)`.
2. Documents are uploaded once and referenced by a server-side `document_id`.
3. Blocking model inference runs in FastAPI thread pools (`run_in_threadpool`) so the main async event loop is never blocked.
