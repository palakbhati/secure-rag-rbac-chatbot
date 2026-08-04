"""
The full guarded pipeline:
Input Guardrail -> RBAC-authorized Retriever -> LLM -> Output Guardrail -> Answer

CHANGED IN PHASE 7: added the input guardrail (runs before any retrieval
or LLM cost is spent) and the output guardrail (runs after generation,
before the answer is returned). A rejected input never reaches RBAC or
the LLM at all — that's the point of putting it first.
"""

import logging

from app.guardrails.input_guardrail import run_input_guardrail
from app.guardrails.output_guardrail import run_output_guardrail
from app.rbac.authorization import authorized_search
from app.schemas.document import DocumentChunk
from app.services.rag.generator import generate
from app.services.rag.prompt import build_messages

logger = logging.getLogger(__name__)


def ask(question: str, role: str, top_k: int = 5) -> dict:
    input_check = run_input_guardrail(question)
    if not input_check.allowed:
        logger.warning("Blocked at input guardrail | role=%s | category=%s | question=%r",
                        role, input_check.category.value, question)
        return {
            "answer": "I can't help with that request.",
            "sources": [],
            "retrieved_departments": [],
            "blocked": True,
            "block_reason": input_check.reason,
        }

    results = authorized_search(question, role=role, top_k=top_k)
    chunks = [DocumentChunk.model_validate(r.payload) for r in results]

    messages = build_messages(question, chunks)
    raw_answer = generate(messages)

    output_check = run_output_guardrail(raw_answer, chunks, role)
    final_answer = output_check.modified_content or raw_answer

    logger.info(
        "Q: %s | role=%s | retrieved %d chunks | departments: %s | output_category=%s",
        question, role, len(chunks), sorted({c.department for c in chunks}), output_check.category.value,
    )

    return {
        "answer": final_answer,
        "sources": [c.document_id for c in chunks],
        "retrieved_departments": sorted({c.department for c in chunks}),
        "blocked": False,
        "output_guardrail_category": output_check.category.value,
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
