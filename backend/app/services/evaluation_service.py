"""
Evaluation service: evaluate generated summaries against reference summaries.

Metrics used:
- ROUGE-1: Unigram overlap between summary and reference (F1-score).
- ROUGE-2: Bigram overlap between summary and reference (F1-score).
- ROUGE-L: Longest Common Subsequence overlap (F1-score).
- BLEU: N-gram precision for sentence generation fluency (sacrebleu).

ROUGE scores are returned as plain Python floats in [0.0, 1.0].
BLEU score is returned as a plain Python float in [0.0, 100.0].
Numpy types from rouge_score are explicitly cast to float for JSON serialisation.
"""

import logging

import sacrebleu
from rouge_score import rouge_scorer

logger = logging.getLogger(__name__)


def evaluate(summary: str, reference: str) -> dict[str, float]:
    """Calculate ROUGE-1, ROUGE-2, ROUGE-L, and BLEU metrics for a summary against a reference text."""
    sum_text = summary.strip()
    ref_text = reference.strip()

    if not sum_text or not ref_text:
        return {
            "rouge_1": 0.0,
            "rouge_2": 0.0,
            "rouge_l": 0.0,
            "bleu": 0.0,
        }

    scorer = rouge_scorer.RougeScorer(["rouge1", "rouge2", "rougeL"], use_stemmer=True)
    rouge_results = scorer.score(ref_text, sum_text)

    bleu_result = sacrebleu.corpus_bleu([sum_text], [[ref_text]])

    return {
        "rouge_1": float(rouge_results["rouge1"].fmeasure),
        "rouge_2": float(rouge_results["rouge2"].fmeasure),
        "rouge_l": float(rouge_results["rougeL"].fmeasure),
        "bleu": float(bleu_result.score),
    }
