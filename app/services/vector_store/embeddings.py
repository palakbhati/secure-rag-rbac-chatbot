"""
Wraps the embedding model. Kept to two responsibilities only: load the
model once, and turn text into vectors. Nothing here knows about Qdrant
or chunks — that separation means swapping embedding models later only
touches this file.
"""

from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.core.config import get_settings


@lru_cache
def _get_model() -> SentenceTransformer:
    settings = get_settings()
    return SentenceTransformer(settings.embedding_model_name)


def get_embedding_dimension() -> int:
    return _get_model().get_sentence_embedding_dimension()


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Batch-embeds a list of strings. Used both when loading chunks into
    Qdrant (Phase 4) and when embedding a user's query at retrieval time
    (Phase 5+) — same function, same model, so query and stored vectors
    are always comparable."""
    model = _get_model()
    vectors = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
    return vectors.tolist()


def embed_text(text: str) -> list[float]:
    return embed_texts([text])[0]