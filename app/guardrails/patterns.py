"""
Deterministic, fast, cheap-to-run patterns. These are LAYER 1 only —
they catch obvious cases before we spend an LLM call on classification.
They will never catch everything; that's what the LLM-based check in
input_guardrail.py is for. Treat additions to this list as improving
recall for the *obvious* cases, not as the whole defense.
"""

import re

# --- Prompt injection heuristics ---
INJECTION_PATTERNS = [
    r"ignore (all |the )?(previous|prior|above) instructions",
    r"disregard (all |the )?(previous|prior|above)",
    r"you are now\b",
    r"forget (all |your )?(previous |prior )?instructions",
    r"reveal (your |the )?(system )?prompt",
    r"what (is|are) your (system )?(prompt|instructions)",
    r"pretend (you are|to be)",
    r"act as (if|though)",
    r"bypass (your |the )?(rules|restrictions|filters|guardrails)",
    r"override (your |the )?(rules|restrictions|instructions)",
    r"jailbreak",
    r"developer mode",
    r"\bDAN\b",  # common "Do Anything Now" jailbreak shorthand
    r"repeat (the|your) (system )?prompt",
    r"print (the|your) (system )?(prompt|instructions)",
]
_COMPILED_INJECTION_PATTERNS = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]


def matches_injection_pattern(text: str) -> str | None:
    for pattern in _COMPILED_INJECTION_PATTERNS:
        if pattern.search(text):
            return pattern.pattern
    return None


# --- PII patterns (used by the output guardrail for redaction) ---
EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_PATTERN = re.compile(r"\b(\+?\d{1,3}[-.\s]?)?\(?\d{3,5}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b")
DATE_OF_BIRTH_PATTERN = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")  # matches the DOB/date format used in hr_data.csv
# Matches currency-like decimal figures, e.g. "1332478.37" or "1,332,478.37"
# — must end in exactly 2 decimal digits, which is what distinguishes a
# salary figure from an ordinary integer count elsewhere in an answer.
CURRENCY_AMOUNT_PATTERN = re.compile(r"\b\d[\d,]*\.\d{2}\b")