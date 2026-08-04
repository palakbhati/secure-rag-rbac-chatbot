"""
Builds the message list sent to the LLM: a system prompt establishing
the ground rules, plus a user turn containing the retrieved context and
the question.

This is a SOFT control, not an enforced one — the model can still ignore
these instructions. Phase 7's output guardrail is what actually checks
groundedness after the fact; this prompt is the first, weakest layer,
not the only one.
"""

from app.schemas.document import DocumentChunk

SYSTEM_PROMPT = """You are an internal assistant for FinSolve Technologies employees.

Rules you must follow:
- Answer ONLY using the information in the provided context. Do not use outside knowledge.
- If the context does not contain enough information to answer, say so plainly. Do not guess.
- Always mention which source document(s) your answer is based on.
- Be concise and factual. Do not speculate about information not present in the context.
"""


def format_context(chunks: list[DocumentChunk]) -> str:
    if not chunks:
        return "(No relevant context was retrieved.)"

    blocks = []
    for chunk in chunks:
        blocks.append(f"[Source: {chunk.document_id} | department: {chunk.department}]\n{chunk.text}")
    return "\n\n---\n\n".join(blocks)


def build_messages(question: str, chunks: list[DocumentChunk]) -> list[dict]:
    context_block = format_context(chunks)
    user_content = (
        f"Context:\n{context_block}\n\n"
        f"Question: {question}\n\n"
        f"Answer using only the context above."
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]