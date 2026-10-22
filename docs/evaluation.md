# Evaluation Metrics Guide (ROUGE & BLEU)

Evaluating text summarization quality requires quantitative comparison against a human-written ground truth reference summary. This system implements standard ROUGE and BLEU metrics.

---

## 1. ROUGE Metrics (Recall-Oriented Understudy for Gisting Evaluation)

ROUGE measures the overlap of n-grams and sequences between a generated summary and a reference summary.

### Metrics Overview

| Metric | Definition | Range | Interpretation |
|---|---|---|---|
| **ROUGE-1** | Unigram (single word) overlap F1-score | 0.0 – 1.0 | High score indicates good topic and vocabulary coverage. |
| **ROUGE-2** | Bigram (two consecutive words) overlap F1-score | 0.0 – 1.0 | Measures local phrasing match and sentence fluency. |
| **ROUGE-L** | Longest Common Subsequence (LCS) F1-score | 0.0 – 1.0 | Measures sentence-level word order preservation without requiring exact n-gram matches. |

### How Scores are Calculated
For each ROUGE metric, precision \(P\), recall \(R\), and harmonic mean F1-score \(F_1\) are computed:
\[
P = \frac{\text{Matching N-grams}}{\text{Total N-grams in Generated Summary}}, \quad R = \frac{\text{Matching N-grams}}{\text{Total N-grams in Reference Summary}}
\]
\[
F_1 = 2 \cdot \frac{P \cdot R}{P + R}
\]
The system reports the \(F_1\) score as a float between `0.0` and `1.0`.

---

## 2. BLEU Metric (Bilingual Evaluation Understudy)

BLEU is an n-gram precision metric modified with a brevity penalty to evaluate sentence generation quality.

* **Package Used**: `sacrebleu`
* **Score Scale**: `0.0` to `100.0`
* **Calculation**: Computes geometric mean of modified n-gram precisions (unigrams through 4-grams) multiplied by a brevity penalty:
\[
\text{BLEU} = \text{BP} \cdot \exp\left( \sum_{n=1}^4 w_n \log p_n \right)
\]

### Interpretation Guidelines
* **80 – 100**: Near-identical or highly accurate paraphrasing.
* **40 – 70**: Strong structural and semantic similarity.
* **20 – 40**: Reasonable content overlap but noticeable vocabulary differences.
* **< 20**: Low overlap; common when comparing abstractive summaries against references written with entirely different phrasing.

---

## 3. Limitations of ROUGE and BLEU

* **Exact Match Dependency**: ROUGE and BLEU rely on word/n-gram overlap. An abstractive summary that uses valid synonyms (e.g., "physician" instead of "doctor") may receive lower scores despite being accurate.
* **Reference Dependency**: Evaluation requires a human-written reference summary.
* **Sensitivity to Sentence Length**: Short reference sentences (under 4 words) yield 0 BLEU score due to missing 4-gram matches.
