"""
Runs on every generated answer, before it reaches the user. Three checks,
in order:

1. UNTRACEABLE PII REDACTION (role-independent): if the answer contains
   something that looks like PII (email, date, currency figure) that
   does NOT appear anywhere in the retrieved context, it's either a
   hallucination or leaked from the model's training data — neither is
   acceptable, regardless of who's asking. This catches a failure mode
   RBAC and role-based redaction don't: the model inventing a plausible
   but fabricated number.

2. ROLE-BASED HR REDACTION (Phase 2's decision): salary/DOB/email figures
   that DO come from retrieved HR content get redacted anyway, unless
   the role is "hr" itself. See pii_redaction.py for the full rationale.

3. GROUNDEDNESS HEURISTIC: word-overlap between the answer and the
   retrieved context. This is intentionally a cheap heuristic, not a
   real faithfulness score — Phase 10 (Ragas) will measure this properly.
   Here, a low score attaches a caveat rather than blocking the answer
   outright, because the heuristic is noisy enough that auto-refusing on
   it would create false-positive refusals on perfectly good answers.
"""

import logging
import re

from app.guardrails.patterns import CURRENCY_AMOUNT_PATTERN, DATE_OF_BIRTH_PATTERN, EMAIL_PATTERN
from app.guardrails.pii_redaction import redact_hr_pii
from app.guardrails.schemas import GuardrailCategory, GuardrailResult
from app.schemas.document import DocumentChunk

logger = logging.getLogger("guardrails.output")

GROUNDEDNESS_WARNING_THRESHOLD = 0.25
_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "of", "to", "in", "on", "for",
    "and", "or", "this", "that", "it", "as", "with", "by", "at", "be", "has", "have",
}


def _redact_untraceable_pii(answer: str, context_text: str) -> tuple[str, bool]:
    redacted = answer
    flagged = False

    for pattern, label in [
        (EMAIL_PATTERN, "[UNVERIFIED EMAIL REMOVED]"),
        (DATE_OF_BIRTH_PATTERN, "[UNVERIFIED DATE REMOVED]"),
    ]:
        for match in list(pattern.finditer(redacted)):
            if match.group() not in context_text:
                redacted = redacted.replace(match.group(), label)
                flagged = True

    for match in list(CURRENCY_AMOUNT_PATTERN.finditer(redacted)):
        if "." in match.group() and match.group() not in context_text:
            redacted = redacted.replace(match.group(), "[UNVERIFIED AMOUNT REMOVED]")
            flagged = True

    return redacted, flagged


def _groundedness_score(answer: str, context_text: str) -> float:
    answer_words = {w for w in re.findall(r"[a-z0-9]+", answer.lower()) if w not in _STOPWORDS and len(w) > 2}
    if not answer_words:
        return 1.0
    context_words = set(re.findall(r"[a-z0-9]+", context_text.lower()))
    overlap = answer_words & context_words
    return len(overlap) / len(answer_words)


def run_output_guardrail(answer: str, chunks: list[DocumentChunk], role: str) -> GuardrailResult:
    context_text = "\n".join(c.text for c in chunks)

    # Step 1: role-independent — redact anything PII-shaped that can't be
    # traced back to retrieved context (catches hallucination/leakage).
    answer, untraceable_flagged = _redact_untraceable_pii(answer, context_text)

    # Step 2: role-based HR redaction (Phase 2 decision).
    answer, hr_flagged = redact_hr_pii(answer, chunks, role)

    # Step 3: groundedness heuristic — attach a caveat, don't block.
    score = _groundedness_score(answer, context_text)
    if score < GROUNDEDNESS_WARNING_THRESHOLD and chunks:
        answer += "\n\n_Note: this answer may not be fully grounded in the retrieved documents — verify before relying on it._"

    if untraceable_flagged or hr_flagged:
        logger.warning(
            "Output guardrail | redacted=True | untraceable_pii=%s | hr_role_redaction=%s | role=%s | groundedness=%.2f",
            untraceable_flagged, hr_flagged, role, score,
        )
        category = GuardrailCategory.PII_LEAK
        reason = "PII redacted from answer"
    elif score < GROUNDEDNESS_WARNING_THRESHOLD:
        category = GuardrailCategory.UNGROUNDED
        reason = f"Low groundedness score ({score:.2f}); caveat attached"
    else:
        category = GuardrailCategory.OK
        reason = "no violations"

    return GuardrailResult(allowed=True, category=category, reason=reason, modified_content=answer)