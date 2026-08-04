"""
Walks resources/data/<department>/*, dispatches each file to the right
loader by extension, and writes every resulting chunk to a single JSONL
file. Phase 4 reads that file to generate embeddings and populate Qdrant
— ingestion and embedding are kept as separate steps so re-embedding
(e.g. after switching models) never requires re-parsing documents.
"""

import json
import logging
from pathlib import Path

from app.schemas.document import DocumentChunk
from app.services.ingestion.csv_loader import load_hr_csv
from app.services.ingestion.markdown_loader import load_and_chunk_markdown

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

DATA_ROOT = Path("resources/data")
OUTPUT_PATH = Path("resources/processed/chunks.jsonl")


def run_ingestion(data_root: Path = DATA_ROOT, output_path: Path = OUTPUT_PATH) -> list[DocumentChunk]:
    all_chunks: list[DocumentChunk] = []

    if not data_root.exists():
        raise FileNotFoundError(f"Data root not found: {data_root}")

    for department_dir in sorted(p for p in data_root.iterdir() if p.is_dir()):
        department = department_dir.name

        for file_path in sorted(department_dir.iterdir()):
            try:
                if file_path.suffix.lower() == ".md":
                    all_chunks.extend(load_and_chunk_markdown(file_path, department))
                elif file_path.suffix.lower() == ".csv":
                    all_chunks.extend(load_hr_csv(file_path, department))
                else:
                    logger.warning("Skipping unsupported file type: %s", file_path)
            except Exception:
                # Log and continue rather than aborting the whole ingestion
                # run over one bad file — but the failure must be visible,
                # never silently swallowed.
                logger.exception("Failed to ingest %s", file_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(chunk.model_dump_json() + "\n")

    logger.info("Ingestion complete: %d total chunks written to %s", len(all_chunks), output_path)
    return all_chunks


if __name__ == "__main__":
    run_ingestion()