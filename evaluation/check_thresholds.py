"""
Runs the full evaluation, then compares scores against
BASELINE_THRESHOLDS and exits non-zero if anything fails. This exit
code is what GitHub Actions (Phase 11's workflow) actually gates on —
a failing exit code fails the CI job, which blocks the merge.

A NaN or missing score is treated as a FAILURE, not skipped — if
scoring silently broke (see evaluate.py's note on Groq rate limiting),
that should block a merge just as loudly as a real quality regression,
not pass by accident because the check didn't know how to compare NaN.
"""

import json
import math
import sys

from evaluation.evaluate import run_evaluation
from evaluation.metrics import BASELINE_THRESHOLDS


def check_thresholds(scores: dict, thresholds: dict = BASELINE_THRESHOLDS) -> tuple[bool, list[str]]:
    failures = []
    for metric, threshold in thresholds.items():
        score = scores.get(metric)
        if score is None or (isinstance(score, float) and math.isnan(score)):
            failures.append(f"{metric}: score is {score!r} (missing or NaN) — treated as a failure, not skipped")
            continue
        if score < threshold:
            failures.append(f"{metric}: {score:.3f} is below threshold {threshold:.3f}")
    return (len(failures) == 0, failures)


if __name__ == "__main__":
    scores = run_evaluation(save=True)
    print(json.dumps(scores, indent=2))

    passed, failures = check_thresholds(scores)

    if not passed:
        print("\nTHRESHOLD CHECK FAILED:")
        for failure in failures:
            print(" -", failure)
        sys.exit(1)

    print("\nAll thresholds passed.")
    sys.exit(0)