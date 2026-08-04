"""
Loads a markdown file, parses it with Docling, and splits it into
header-aware chunks with metadata attached.

Two-stage splitting:
  1. MarkdownHeaderTextSplitter groups content under its nearest heading
     (so a table or list stays with the section that explains it).
  2. RecursiveCharacterTextSplitter further splits any section that's
     still too large, with overlap so meaning isn't severed at the cut.
"""

import logging
from pathlib import Path

from docling.document_converter import DocumentConverter
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from app.schemas.document import Classification, DocType, DocumentChunk
from app.services.ingestion.access_control_map import get_access_rules

logger = logging.getLogger(__name__)

CHUNK_SIZE = 900
CHUNK_OVERLAP = 150

HEADERS_TO_SPLIT_ON = [
    ("#", "h1"),
    ("##", "h2"),
    ("###", "h3"),
]

_docling_converter = DocumentConverter()


def _parse_to_markdown(file_path: Path) -> str:
    """Run the file through Docling. For an already-markdown source this
    mainly normalizes structure, but keeping Docling in the path means
    swapping in PDFs/DOCX files later (Phase 3.1, if the dataset grows)
    requires no change to the chunking logic below."""
    result = _docling_converter.convert(str(file_path))
    return result.document.export_to_markdown()


def load_and_chunk_markdown(file_path: Path, department: str) -> list[DocumentChunk]:
    rules = get_access_rules(department)
    raw_markdown = _parse_to_markdown(file_path)

    header_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=HEADERS_TO_SPLIT_ON)
    header_sections = header_splitter.split_text(raw_markdown)

    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )

    chunks: list[DocumentChunk] = []
    chunk_index = 0

    for section in header_sections:
        # Prefer the most specific heading available for traceability
        heading = (
            section.metadata.get("h3")
            or section.metadata.get("h2")
            or section.metadata.get("h1")
            or file_path.stem
        )

        for piece in char_splitter.split_text(section.page_content):
            if not piece.strip():
                continue
            chunks.append(
                DocumentChunk(
                    document_id=f"{file_path.stem}_{chunk_index}",
                    department=department,
                    classification=rules["classification"],
                    allowed_roles=rules["allowed_roles"],
                    doc_type=DocType.MARKDOWN,
                    source_path=str(file_path),
                    contains_pii=rules["contains_pii"],
                    text=piece.strip(),
                    chunk_index=chunk_index,
                    section_heading=heading,
                )
            )
            chunk_index += 1

    logger.info("Parsed %s into %d chunks (department=%s)", file_path.name, len(chunks), department)
    return chunks