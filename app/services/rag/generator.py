"""
Thin wrapper around the Groq-hosted LLM call. The model name is never
hardcoded here (Rule #9) — it comes from Settings, so switching models
is a .env change, not a code change.

@traceable on generate() gives this call a clearly named span in
LangSmith ("llm_generate"), nested inside whatever span called it
(the "rag_pipeline" span in pipeline.py). The actual ChatGroq call
underneath is ALSO auto-traced by LangChain's own tracer (as an "llm"
run type) when LANGSMITH_TRACING is on — that inner span is where
token counts (input/output/total) actually show up, captured
automatically, with no manual extraction needed here.
"""

from functools import lru_cache

from langchain_groq import ChatGroq
from langsmith import traceable

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


@traceable(name="llm_generate", run_type="chain")
def generate(messages: list[dict]) -> str:
    llm = get_llm()
    response = llm.invoke(messages)
    return response.content