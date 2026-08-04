"""
All Qdrant interaction lives here. Two things worth noting:

1. `qdrant_url` unset -> local on-disk mode (qdrant-client embeds the
   engine directly, no server process needed). This keeps local dev
   frictionless; Phase 13/14 point QDRANT_URL at a real server without
   any code change here.

2. `search()` takes an optional `allowed_role` filter and applies it as
   a Qdrant-side payload filter, not a post-query Python filter. This is
   the mechanism Phase 6's RBAC will call directly — filtering happens
   inside the vector database, before results ever reach the LLM.
"""

import logging
from functools import lru_cache

from qdrant_client import QdrantClient, models

from app.core.config import get_settings
from app.schemas.document import DocumentChunk
from app.services.vector_store.embeddings import embed_text, embed_texts, get_embedding_dimension

logger = logging.getLogger(__name__)


@lru_cache
def get_client() -> QdrantClient:
    settings = get_settings()
    if settings.qdrant_url:
        return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key)
    logger.info("QDRANT_URL not set — using local on-disk Qdrant at %s", settings.qdrant_local_path)
    return QdrantClient(path=settings.qdrant_local_path)


def ensure_collection(recreate: bool = False) -> None:
    """Creates the collection if it doesn't exist. `recreate=True` wipes
    and rebuilds it — useful when re-ingesting after a chunking change,
    but destructive, so it's never the default."""
    settings = get_settings()
    client = get_client()
    collection_name = settings.qdrant_collection_name

    exists = client.collection_exists(collection_name)
    if exists and not recreate:
        return

    if exists and recreate:
        client.delete_collection(collection_name)

    client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(
            size=get_embedding_dimension(),
            distance=models.Distance.COSINE,
        ),
    )

    # Index allowed_roles explicitly so role-based filtering (Phase 6) is
    # fast rather than a full scan, even as the collection grows.
    client.create_payload_index(
        collection_name=collection_name,
        field_name="allowed_roles",
        field_schema=models.PayloadSchemaType.KEYWORD,
    )
    logger.info("Created collection '%s' (dim=%d)", collection_name, get_embedding_dimension())


def upsert_chunks(chunks: list[DocumentChunk], batch_size: int = 64) -> None:
    settings = get_settings()
    client = get_client()

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        vectors = embed_texts([c.text for c in batch])
        points = [
            models.PointStruct(
                id=i + j,  # simple sequential ID; document_id is kept in payload for traceability
                vector=vector,
                payload=chunk.model_dump(mode="json"),
            )
            for j, (chunk, vector) in enumerate(zip(batch, vectors))
        ]
        client.upsert(collection_name=settings.qdrant_collection_name, points=points)

    logger.info("Upserted %d chunks into '%s'", len(chunks), settings.qdrant_collection_name)


def search(
    query: str,
    top_k: int = 5,
    allowed_role: str | None = None,
) -> list[models.ScoredPoint]:
    """Bare similarity search, with an optional Qdrant-side role filter.

    NOTE: this function is the retrieval primitive — it does not decide
    RBAC policy itself. Phase 6 will wrap this with the actual
    authorization logic (which role is allowed to ask at all, audit
    logging, etc.). This function only provides the mechanism: filter
    by `allowed_role` if given, otherwise search unfiltered.
    """
    settings = get_settings()
    client = get_client()
    query_vector = embed_text(query)

    query_filter = None
    if allowed_role:
        query_filter = models.Filter(
            must=[models.FieldCondition(key="allowed_roles", match=models.MatchValue(value=allowed_role))]
        )

    results = client.query_points(
        collection_name=settings.qdrant_collection_name,
        query=query_vector,
        query_filter=query_filter,
        limit=top_k,
    )
    return results.points