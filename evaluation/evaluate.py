"""
Runs every example in dataset.py through the real pipeline (ask()), then
scores the results with Ragas using Groq as the judge LLM and the same
local embedding model the app itself uses.

COLUMN NAMES, verified against the actually-installed ragas package
before writing this (not assumed from older tutorials): current ragas
expects `user_input` / `response` / `retrieved_contexts` / `reference`.
Older tutorials and some cached docs use `question` / `answer` /
`contexts` / `ground_truth` — I tested this directly: passing the old
names doesn't error, it silently builds a dataset where every field is
None, which would have produced either a crash deep in scoring or
meaningless NaN-ish results with no clear error pointing at the cause.
If you're on a different ragas version and see similar silent failures,
check `EvaluationDataset.from_list([...])[0]` directly — if the fields
come back None, it's a naming mismatch, not a data problem.

RATE LIMITS: `evaluate()` runs metric scoring CONCURRENTLY across
examples and metrics by default (`RunConfig.max_workers` defaults to
16), which can burst past Groq's rate limit — faithfulness in
particular makes MORE LLM calls per example than the other three
metrics (it decomposes the answer into claims as a separate call before
checking each one), so it's disproportionately likely to be the metric
that trips a 429 and silently comes back as NaN. `max_workers` is
lowered below to reduce burst concurrency; if you're still seeing NaN
after that, run with `debug=True` (below) to see the real exception
instead of a silently-swallowed one.

Results are saved to resources/evaluation/results_<timestamp>.json —
Phase 11's GitHub Actions workflow will read the latest of these and
compare against BASELINE_THRESHOLDS (metrics.py) to pass/fail a build.
"""

import json
import logging
import math
from datetime import datetime, timezone
from pathlib import Path

from langchain_huggingface import HuggingFaceEmbeddings
from ragas import EvaluationDataset, evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.run_config import RunConfig

from app.core.config import get_settings
from evaluation.dataset import EVAL_EXAMPLES
from evaluation.metrics import RAGAS_METRICS

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

RESULTS_DIR = Path("resources/evaluation")


def _run_pipeline_on_dataset() -> list[dict]:
    """Runs each eval example through the real ask() pipeline and collects
    what Ragas needs, using ragas's actual current field names directly
    (not an intermediate naming we'd have to translate later)."""
    # Imported here, not at module load time, so this file can be imported
    # (e.g. by tests) without requiring GROQ_API_KEY to be set.
    from app.services.rag.pipeline import ask

    rows = []
    for example in EVAL_EXAMPLES:
        result = ask(example["question"], role=example["role"])
        rows.append({
            "user_input": example["question"],
            "response": result["answer"],
            "retrieved_contexts": result["context_texts"] or ["(no context retrieved)"],
            "reference": example["ground_truth"],
        })
        logger.info("Evaluated: %r (role=%s) -> %d context chunks",
                    example["question"], example["role"], len(result["context_texts"]))
    return rows


def run_evaluation(save: bool = True, debug: bool = False) -> dict:
    """`debug=True` sets raise_exceptions=True, so a failing metric call
    raises immediately with the real traceback instead of being recorded
    as NaN. Use this to diagnose a NaN score; leave it False for normal
    runs (including CI, Phase 11) since a real, non-transient failure in
    ONE example shouldn't be allowed to crash the entire evaluation run
    for every other example too."""
    settings = get_settings()

    rows = _run_pipeline_on_dataset()
    dataset = EvaluationDataset.from_list(rows)

    judge_llm = LangchainLLMWrapper(_build_judge_llm())
    judge_embeddings = LangchainEmbeddingsWrapper(HuggingFaceEmbeddings(model_name=settings.embedding_model_name))

    # Lower than the default (16) — fewer concurrent requests to Groq
    # reduces the chance of tripping its rate limit mid-run.
    run_config = RunConfig(
        max_workers=1,
        timeout=600,
    )

    result = evaluate(
        dataset,
        metrics=RAGAS_METRICS,
        llm=judge_llm,
        embeddings=judge_embeddings,
        run_config=run_config,
        raise_exceptions=debug,
    )
    scores = result.to_pandas()[[m.name for m in RAGAS_METRICS]].mean().to_dict()

    nan_metrics = [name for name, value in scores.items() if isinstance(value, float) and math.isnan(value)]
    if nan_metrics:
        logger.warning(
            "Metric(s) came back NaN: %s — this means scoring raised an exception on every "
            "example for that metric and evaluate() swallowed it (raise_exceptions=False). "
            "Re-run with run_evaluation(debug=True) to see the real traceback. Common causes: "
            "Groq rate limiting (faithfulness makes extra LLM calls per example), or a judge "
            "model that doesn't support the structured output this metric needs.",
            nan_metrics,
        )

    logger.info("Evaluation complete | scores: %s", scores)

    if save:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_path = RESULTS_DIR / f"results_{timestamp}.json"
        out_path.write_text(json.dumps({"timestamp": timestamp, "scores": scores, "n_examples": len(rows)}, indent=2))
        logger.info("Saved results to %s", out_path)

    return scores


def _build_judge_llm():
    from app.services.rag.generator import get_llm
    return get_llm()


if __name__ == "__main__":
    import sys

    debug_mode = "--debug" in sys.argv
    scores = run_evaluation(debug=debug_mode)
    print(json.dumps(scores, indent=2))