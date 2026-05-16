from __future__ import annotations

import re
from dataclasses import dataclass


SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'])")


@dataclass(frozen=True)
class DocumentChunk:
    id: str
    text: str
    source: str
    heading: str | None = None


def split_sentences(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []

    sentences = [part.strip(" -\t") for part in SENTENCE_RE.split(normalized)]
    return [sentence for sentence in sentences if len(sentence) > 12]


def chunk_text(text: str, source: str = "document") -> list[DocumentChunk]:
    chunks: list[DocumentChunk] = []
    current_heading: str | None = None
    counter = 1

    blocks = [block.strip() for block in text.split("\n") if block.strip()]
    for block in blocks:
        if _looks_like_heading(block):
            current_heading = block.strip("# ").strip()
            continue

        for sentence in split_sentences(block):
            chunk_id = f"{source[:1].upper()}{counter:03d}"
            chunks.append(
                DocumentChunk(
                    id=chunk_id,
                    text=sentence,
                    source=source,
                    heading=current_heading,
                )
            )
            counter += 1

    return chunks


def _looks_like_heading(block: str) -> bool:
    stripped = block.strip()
    if stripped.startswith("#"):
        return True
    if len(stripped) > 90:
        return False
    if stripped.endswith("."):
        return False
    words = stripped.split()
    if not words:
        return False
    title_case_count = sum(1 for word in words if word[:1].isupper())
    return len(words) <= 8 and title_case_count >= max(1, len(words) - 1)
