"""
Thin wrapper around the Groq-hosted LLM call. The model name is never
hardcoded here (Rule #9) — it comes from Settings, so switching models
is a .env change, not a code change.
"""

from functools import lru_cache

from langchain_groq import ChatGroq

from app.core.config import get_settings


@lru_cache
def get_llm() -> ChatGroq:
    settings = get_settings()
    if not settings.groq_api_key:
        raise ValueError(
            "GROQ_API_KEY is not set. Add it to your .env file — "
            "get a key at https://console.groq.com"
        )
    return ChatGroq(
        model=settings.groq_model_name,
        api_key=settings.groq_api_key,
        temperature=0,  # deterministic, factual answers over creative ones — this is an internal Q&A tool, not a writing assistant
    )


def generate(messages: list[dict]) -> str:
    llm = get_llm()
    response = llm.invoke(messages)
    return response.content