"""
The full guarded, traced pipeline:
Input Guardrail -> RBAC-authorized Retriever -> LLM -> Output Guardrail -> Answer

CHANGED IN PHASE 7: added the input guardrail (runs before any retrieval
or LLM cost is spent) and the output guardrail (runs after generation,
before the answer is returned). A rejected input never reaches RBAC or
the LLM at all — that's the point of putting it first.

CHANGED IN PHASE 9:
- `@traceable` on `ask()` makes this the root span in LangSmith; every
  function it calls that's ALSO decorated (`authorized_search`,
  `run_input_guardrail`, `generate`, `run_output_guardrail`) nests
  underneath it automatically — one trace tree per question, in order.
- `@traceable` auto-captures a function's arguments and return value as
  the run's inputs/outputs. This is why `ask(question, role, ...)`
  already gives you question + role in every trace with zero extra
  plumbing — no manual metadata wiring needed for the basics.
- Added a `user_id` parameter distinct from `role` — role is what RBAC
  and guardrails need to make decisions; user_id is who to blame/credit
  in an audit log or a cost report (Phase 12) when several people share
  the same role.
- Added error handling around retrieval/generation: previously an
  exception here (e.g. Groq timeout) would crash the whole call with an
  unhandled traceback. Now it's caught, logged with full context, and
  surfaced to the caller as a graceful error response — and LangSmith
  still records it as a failed run either way, since @traceable logs
  exceptions before they propagate.
"""

import logging

from langsmith import traceable

from app.guardrails.input_guardrail import run_input_guardrail
from app.guardrails.output_guardrail import run_output_guardrail
from app.rbac.authorization import authorized_search
from app.schemas.document import DocumentChunk
from app.services.monitoring.tracing import configure_langsmith
from app.services.rag.generator import generate
from app.services.rag.prompt import build_messages

configure_langsmith()  # must run before any @traceable call fires, or tracing is silently a no-op

logger = logging.getLogger(__name__)


@traceable(name="rag_pipeline", run_type="chain")
def ask(question: str, role: str, user_id: str | None = None, top_k: int = 5) -> dict:
    input_check = run_input_guardrail(question)
    if not input_check.allowed:
        logger.warning("Blocked at input guardrail | user=%s | role=%s | category=%s | question=%r",
                        user_id, role, input_check.category.value, question)
        return {
            "answer": "I can't help with that request.",
            "sources": [],
            "retrieved_departments": [],
            "blocked": True,
            "block_reason": input_check.reason,
        }

    try:
        results = authorized_search(question, role=role, top_k=top_k)
        chunks = [DocumentChunk.model_validate(r.payload) for r in results]

        messages = build_messages(question, chunks)
        raw_answer = generate(messages)

        output_check = run_output_guardrail(raw_answer, chunks, role)
        final_answer = output_check.modified_content or raw_answer
    except Exception:
        logger.exception("Pipeline error | user=%s | role=%s | question=%r", user_id, role, question)
        return {
            "answer": "Something went wrong while processing your question. Please try again.",
            "sources": [],
            "retrieved_departments": [],
            "blocked": False,
            "error": True,
        }

    logger.info(
        "Q: %s | user=%s | role=%s | retrieved %d chunks | departments: %s | output_category=%s",
        question, user_id, role, len(chunks), sorted({c.department for c in chunks}), output_check.category.value,
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