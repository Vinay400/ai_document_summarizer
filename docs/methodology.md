# Summarization Methodology

This document explains the principles, algorithms, and trade-offs of the three summarization strategies implemented in this platform: Extractive, Abstractive, and Hybrid.

---

## 1. Extractive Summarization (Embeddings + TextRank)

### How It Works
1. **Sentence Segmentation**: The input text is split into distinct sentences using NLTK Punkt (or regex fallback).
2. **Dense Vector Embeddings**: Each sentence is transformed into a dense vector embedding using `sentence-transformers/all-MiniLM-L6-v2`.
3. **Cosine Similarity Matrix**: A similarity matrix is constructed where entry \(S_{ij}\) represents the cosine similarity between the embeddings of sentence \(i\) and sentence \(j\). Negative similarity values are clipped to zero, and the diagonal is zeroed.
4. **TextRank Graph Scoring**: PageRank is executed over the similarity graph using NetworkX. Sentences that share high semantic similarity with many other sentences receive high central rank scores.
5. **Selection & Reordering**: The top \(k\) sentences based on rank (determined by requested length ratio) are selected and reassembled into their original document sequence.

### Advantages & Limits
* **Zero Hallucination**: Every sentence is quoted verbatim from the source.
* **Factual Integrity**: Ideal for legal, financial, or medical documents where exact wording matters.
* **Limitation**: Cannot synthesize or rewrite text into more concise prose; may retain redundant phrasing if sentence structure is verbose.

---

## 2. Abstractive Summarization (BART + Map-Reduce)

### How It Works
1. **Short Input Guard**: Inputs under 40 words are returned as-is to prevent unnatural expansion.
2. **Single Pass Generation**: If token count is \(\le 900\) tokens, the document is passed directly through `facebook/bart-large-cnn` (a Sequence-to-Sequence Transformer with bidirectional encoder and autoregressive decoder).
3. **Map-Reduce for Long Documents**:
   * **Map Phase**: Documents exceeding token limits are split into sentence-aligned overlapping chunks using `chunking_service`. Each chunk is summarized independently by BART.
   * **Reduce Phase**: Partial summaries are concatenated. If the joined summary still exceeds 900 tokens, it is chunked and condensed one final time.

### Generation Parameters
Generation length is controlled via `LENGTH_SETTINGS`:
* **Short**: `max_new_tokens`: 120, `min_new_tokens`: 40
* **Medium**: `max_new_tokens`: 220, `min_new_tokens`: 80
* **Long**: `max_new_tokens`: 400, `min_new_tokens`: 140

### Advantages & Limits
* **Fluency & Conciseness**: Generates fresh, human-like sentences that combine multiple ideas.
* **Limitation**: Like all generative sequence-to-sequence models, it carries a small risk of hallucinating details or ungrounded facts.

---

## 3. Hybrid Summarization (TextRank Filter + BART Condensation)

### How It Works
1. **Extractive Pre-Filtering**: The document is split into sentences and scored using TextRank (`extractive_service.rank_sentences`).
2. **Top Content Selection**: The top ~50% highest-ranking sentences are selected and restored to original document order.
3. **Abstractive Condensation**: The extractively filtered text is fed into `abstractive_service.summarize` for BART condensation.

### Why Hybrid?
* **Constrained Generation**: By removing low-relevance filler sentences before BART sees the text, the language model receives only core factual statements.
* **Best of Both Worlds**: Combines the strict factual grounding of extractive rank filtering with the linguistic fluency and conciseness of abstractive generation.
