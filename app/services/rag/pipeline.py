"""
The baseline pipeline: question -> retriever -> context -> LLM -> answer.

Deliberately NO role filtering and NO guardrails here — this is Phase 5's
whole point, a working baseline to sanity-check manually before Phase 6
(RBAC) and Phase 7 (guardrails) wrap around it. Do not point this
pipeline at real users; Phase 6 replaces `search()`'s unfiltered call
with a role-filtered one before this becomes user-facing.
"""

import logging

from app.schemas.document import DocumentChunk
from app.services.rag.generator import generate
from app.services.rag.prompt import build_messages
from app.services.vector_store.qdrant_store import search

logger = logging.getLogger(__name__)


def ask(question: str, top_k: int = 5) -> dict:
    results = search(question, top_k=top_k)  # unfiltered — Phase 6 adds allowed_role here
    chunks = [DocumentChunk.model_validate(r.payload) for r in results]

    messages = build_messages(question, chunks)
    answer = generate(messages)

    logger.info("Q: %s | retrieved %d chunks | departments: %s",
                question, len(chunks), sorted({c.department for c in chunks}))

    return {
        "answer": answer,
        "sources": [c.document_id for c in chunks],
        "retrieved_departments": sorted({c.department for c in chunks}),
    }


if __name__ == "__main__":
    import sys

    question = " ".join(sys.argv[1:]) or "What is FinSolve's leave policy?"
    result = ask(question)
    print("Question:", question)
    print("\nAnswer:", result["answer"])
    print("\nSources:", result["sources"])