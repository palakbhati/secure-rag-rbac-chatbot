"""
Redacts specific PII fields from the generated answer — but only when
(a) HR content was actually part of the retrieved context, AND
(b) the requesting role is not "hr" itself.

This is the concrete enforcement of the Phase 2 decision: executives
(and anyone else who could theoretically reach HR content) get
retrieval access, but individual salary/DOB/personal-email figures are
redacted from what they're shown. HR itself needs those figures for
its actual job, so HR is exempted.

Known limitation, stated plainly: the currency-amount pattern is broad
(it matches any decimal number), so redaction is scoped to only fire
when HR chunks were in context — this keeps false positives (redacting
an unrelated number, e.g. a revenue figure) rare in practice, but it's
a heuristic, not a guarantee. Phase 10's evaluation should measure this
directly; tightening this further is a good candidate for iteration
once we have real eval data instead of guesses.
"""

from app.guardrails.patterns import CURRENCY_AMOUNT_PATTERN, DATE_OF_BIRTH_PATTERN, EMAIL_PATTERN
from app.schemas.document import DocumentChunk


def redact_hr_pii(answer: str, chunks: list[DocumentChunk], role: str) -> tuple[str, bool]:
    """Returns (possibly redacted answer, whether anything was redacted)."""
    hr_content_in_context = any(c.department == "hr" for c in chunks)

    if not hr_content_in_context or role == "hr":
        return answer, False

    redacted = answer
    was_redacted = False

    if EMAIL_PATTERN.search(redacted):
        redacted = EMAIL_PATTERN.sub("[REDACTED EMAIL]", redacted)
        was_redacted = True

    if DATE_OF_BIRTH_PATTERN.search(redacted):
        redacted = DATE_OF_BIRTH_PATTERN.sub("[REDACTED DATE]", redacted)
        was_redacted = True

    # Only redact currency-looking numbers with 2 decimal places (matches
    # the salary format in hr_data.csv) — deliberately narrower than the
    # full CURRENCY_AMOUNT_PATTERN to avoid nuking every plain integer
    # (e.g. "22 leave days") in the answer.
    salary_pattern = CURRENCY_AMOUNT_PATTERN
    for match in list(salary_pattern.finditer(redacted)):
        if "." in match.group():
            redacted = redacted.replace(match.group(), "[REDACTED AMOUNT]")
            was_redacted = True

    return redacted, was_redacted