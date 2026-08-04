"""
The RBAC-aware pipeline: question -> RBAC-authorized retriever -> context
-> LLM -> answer.

CHANGED IN PHASE 6: `ask()` now requires a `role` argument and routes
retrieval through `app.rbac.authorization.authorized_search()` instead
of calling the vector store directly. This is deliberate — there should
be exactly one path into the vector store, and it must always validate
the role first. Guardrails (input/output validation) still don't exist
yet — that's Phase 7.
"""

import logging

from app.rbac.authorization import authorized_search
from app.schemas.document import DocumentChunk
from app.services.rag.generator import generate
from app.services.rag.prompt import build_messages

logger = logging.getLogger(__name__)


def ask(question: str, role: str, top_k: int = 5) -> dict:
    results = authorized_search(question, role=role, top_k=top_k)
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

    if len(sys.argv) < 2:
        print("Usage: python -m app.services.rag.pipeline <role> <question...>")
        print("Roles: engineering, finance, marketing, hr, executive")
        sys.exit(1)

    role = sys.argv[1]
    question = " ".join(sys.argv[2:]) or "What is FinSolve's leave policy?"
    result = ask(question, role=role)
    print("Role:", role)
    print("Question:", question)
    print("\nAnswer:", result["answer"])
    print("\nSources:", result["sources"])