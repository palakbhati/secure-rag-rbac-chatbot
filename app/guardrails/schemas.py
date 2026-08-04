"""
Shared result shape for every guardrail check. Keeping input and output
guardrails returning the same shape means the pipeline can log and
handle both uniformly, and Phase 9's monitoring can track "guardrail
violations" as one consistent event type instead of several.
"""

from enum import Enum

from pydantic import BaseModel


class GuardrailCategory(str, Enum):
    OK = "ok"
    PROMPT_INJECTION = "prompt_injection"
    OUT_OF_SCOPE = "out_of_scope"
    PII_LEAK = "pii_leak"
    UNGROUNDED = "ungrounded"
    UNAUTHORIZED_INFO = "unauthorized_info"


class GuardrailResult(BaseModel):
    allowed: bool
    category: GuardrailCategory
    reason: str
    # For output guardrails only: the (possibly redacted/modified) text
    # that should actually be shown to the user.
    modified_content: str | None = None