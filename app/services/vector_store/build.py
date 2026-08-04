"""
Reads resources/processed/chunks.jsonl (Phase 3's output), embeds every
chunk, and loads them into Qdrant. Kept as a separate step from
ingestion so re-embedding (e.g. after switching embedding models) never
requires re-parsing the source documents.
"""

import json
import logging
from pathlib import Path

from app.schemas.document import DocumentChunk
from app.services.vector_store.qdrant_store import ensure_collection, upsert_chunks

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

CHUNKS_PATH = Path("resources/processed/chunks.jsonl")


def load_chunks(path: Path = CHUNKS_PATH) -> list[DocumentChunk]:
    if not path.exists():
        raise FileNotFoundError(f"{path} not found — run Phase 3's ingestion pipeline first.")
    chunks = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            chunks.append(DocumentChunk.model_validate(json.loads(line)))
    return chunks


def build_vector_store(recreate: bool = False) -> None:
    chunks = load_chunks()
    ensure_collection(recreate=recreate)
    upsert_chunks(chunks)
    logger.info("Vector store build complete: %d chunks embedded and stored.", len(chunks))


if __name__ == "__main__":
    build_vector_store(recreate=True)