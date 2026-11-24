from dataclasses import dataclass
from typing import Any

from app.core.config import settings
from app.services.extraction import ExtractedSection


@dataclass
class TextChunk:
    index: int
    content: str
    metadata: dict[str, Any]


def _split_text(text: str) -> list[str]:
    text = text.strip()
    if not text:
        return []

    size = settings.CHUNK_SIZE
    overlap = settings.CHUNK_OVERLAP
    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            boundary = max(
                text.rfind("\n", start + size // 2, end),
                text.rfind(". ", start + size // 2, end),
                text.rfind(" ", start + size // 2, end),
            )
            if boundary > start:
                end = boundary + 1

        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(text):
            break
        start = max(start + 1, end - overlap)

    return chunks


def create_chunks(sections: list[ExtractedSection]) -> list[TextChunk]:
    chunks: list[TextChunk] = []
    for section in sections:
        for piece in _split_text(section.text):
            chunks.append(
                TextChunk(
                    index=len(chunks),
                    content=piece,
                    metadata=dict(section.metadata),
                )
            )
    return chunks
