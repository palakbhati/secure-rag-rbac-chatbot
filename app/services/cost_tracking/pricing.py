"""
Pricing per model, in USD per 1 MILLION tokens. Kept as a plain data
table, separate from any calculation logic (tracker.py), so updating a
price or adding a model is a one-line data change, never a code change.

Verified against multiple independent sources as of August 2026 —
Groq's own pricing page (console.groq.com/pricing) is the authoritative
source; re-check there before relying on these numbers for anything
beyond monitoring/estimation. Groq's pricing is usage-based and can
change; this table is not fetched live.
"""

# {model_name: {"input": $ per 1M input tokens, "output": $ per 1M output tokens}}
GROQ_PRICING_PER_MILLION_TOKENS: dict[str, dict[str, float]] = {
    "llama-3.1-8b-instant": {"input": 0.05, "output": 0.08},
    "llama-3.3-70b-versatile": {"input": 0.59, "output": 0.79},
    "openai/gpt-oss-20b": {"input": 0.075, "output": 0.30},
    "openai/gpt-oss-120b": {"input": 0.15, "output": 0.60},
}


def get_price_per_million(model_name: str) -> dict[str, float]:
    """Raises on an unknown model rather than silently assuming a price —
    an unrecognized model should surface as 'go add pricing for this',
    not silently report $0.00 or some other model's rate."""
    if model_name not in GROQ_PRICING_PER_MILLION_TOKENS:
        raise ValueError(
            f"No pricing configured for model '{model_name}'. "
            f"Add it to GROQ_PRICING_PER_MILLION_TOKENS in pricing.py — "
            f"check current rates at https://console.groq.com/pricing"
        )
    return GROQ_PRICING_PER_MILLION_TOKENS[model_name]


def calculate_cost(model_name: str, input_tokens: int, output_tokens: int) -> float:
    prices = get_price_per_million(model_name)
    input_cost = (input_tokens / 1_000_000) * prices["input"]
    output_cost = (output_tokens / 1_000_000) * prices["output"]
    return input_cost + output_cost