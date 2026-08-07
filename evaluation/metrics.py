"""
The four core RAG metrics, and why each one is here:

- faithfulness: does the answer's claims trace back to retrieved context?
  Catches hallucination. Reference-free (doesn't need ground_truth).
- answer_relevancy: does the answer address the question asked? Catches
  "grounded but rambling / answering a different question." Reference-free.
- context_precision: of the chunks retrieved, how many were relevant?
  Catches retriever noise. Reference-free.
- context_recall: did retrieval get everything needed? Catches missed
  context. Needs `ground_truth` — the one metric here that does.

All four together answer your original spec's four areas: faithfulness,
context relevance (precision), answer relevance, and retrieval quality
(precision + recall together).
"""

from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness

RAGAS_METRICS = [faithfulness, answer_relevancy, context_precision, context_recall]

# Baseline thresholds — Phase 11's CI will compare a new run's scores
# against these. Set from typical Ragas literature defaults for a first
# baseline, NOT tuned to this specific dataset yet — see the note in
# Phase 11 about revisiting these once we have several real runs to look at.
BASELINE_THRESHOLDS = {
    "faithfulness": 0.70,
    "answer_relevancy": 0.70,
    "context_precision": 0.60,
    "context_recall": 0.60,
}