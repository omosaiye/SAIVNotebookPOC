from __future__ import annotations

from services.api.app.chat.retrieval import RetrievedChunk


def build_grounded_prompt(*, query: str, chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return (
            "No indexed context is currently available for this query. "
            f"User question: {query}"
        )

    context_lines = [
        f"[{idx + 1}] {chunk.file_name}: {chunk.text}"
        for idx, chunk in enumerate(chunks)
    ]
    joined = "\n".join(context_lines)
    return (
        "Answer the user using only the provided grounded context.\n"
        f"Question: {query}\n"
        f"Context:\n{joined}"
    )

