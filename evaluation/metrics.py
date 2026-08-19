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

# Baseline thresholds — Phase 11's CI compares a new run's scores against
# these and fails the build if any metric drops below its floor.
#
# CALIBRATED FROM TWO REAL BASELINE RUNS (Phase 10, 10 examples each),
# not a single run and not literature defaults. The two runs revealed
# real, substantial run-to-run noise from the LLM-judge scoring on this
# small (10-example) dataset:
#
#   metric              run 1     run 2     spread
#   faithfulness        NaN       0.695     n/a (only 1 clean run)
#   answer_relevancy    0.9255    0.9255    0.000  <- rock stable
#   context_precision   0.750     0.575     0.175  <- noisy
#   context_recall      0.464     0.714     0.250  <- very noisy
#
# Thresholds below are set beneath the LOWER of the two observed runs,
# not beneath their average — a floor should survive the worst run
# we've actually seen, not just a typical one. Metrics with wide
# observed spread (context_precision, context_recall) get set well
# below their low point, since one more noisy run landing even lower
# than what we've seen so far is a real possibility, not a hypothetical
# — this dataset is only 10 examples, and small eval sets are noisy by
# nature. answer_relevancy's perfect stability across both runs earns
# it a tighter margin; it's actually a trustworthy signal so far.
#
# THIS IS A "DON'T REGRESS FROM TODAY" FLOOR, NOT A QUALITY TARGET.
# A passing CI run does not mean the pipeline is good enough to ship —
# context_precision and context_recall in particular are known weak
# spots. As the pipeline genuinely improves AND the eval dataset grows
# beyond 10 examples (which will itself reduce noise), re-run baseline
# a few times and RAISE these thresholds to lock in real improvement.
# That ratchet is intentional, not a one-time setup step.
# ⚠️ STALE AS OF 2026-08-19: these thresholds were calibrated using
# llama-3.1-8b-instant as BOTH the generation model and the Ragas judge
# model (config.py's default at the time). Groq decommissioned that
# model on 2026-08-16; the default is now openai/gpt-oss-20b (see
# config.py's migration note). A different model can score meaningfully
# differently on the exact same questions — these numbers have NOT been
# re-verified against the new default. Until you re-run
# `python -m evaluation.evaluate --debug` against the new model and
# update the table below, treat CI's current pass/fail as informative
# but not fully trustworthy: a real regression could pass, or a
# perfectly fine answer under the new model could fail, purely because
# the floor was set for a different model's behavior.
BASELINE_THRESHOLDS = {
    "faithfulness": 0.60,  # only 1 clean measurement (0.695) — kept conservative until more runs exist
    "answer_relevancy": 0.88,  # observed 0.9255 twice, identically — tight margin is justified here
    "context_precision": 0.45,  # observed 0.575-0.750 — floor set below the low end, given the 0.175 spread
    "context_recall": 0.35,  # observed 0.464-0.714 — floor set below the low end, given the 0.250 spread
}