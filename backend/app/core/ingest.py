from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path


SUPPORTED_TEXT_EXTENSIONS = {".txt", ".md", ".markdown"}
SUPPORTED_EXTENSIONS = SUPPORTED_TEXT_EXTENSIONS | {".pdf"}


class IngestError(ValueError):
    """Raised when uploaded content cannot be safely ingested."""


@dataclass(frozen=True)
class IngestedDocument:
    title: str
    text: str


def normalize_text(text: str) -> str:
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def document_from_text(text: str | None, title: str | None = None) -> IngestedDocument:
    if not text or not normalize_text(text):
        raise IngestError("Document text is empty.")

    normalized = normalize_text(text)
    if len(normalized) < 80:
        raise IngestError("Document is too short for a meaningful audit.")

    return IngestedDocument(title=title or "Untitled document", text=normalized)


def text_from_bytes(filename: str, content: bytes) -> IngestedDocument:
    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise IngestError(f"Unsupported file type '{suffix}'. Supported types: {supported}.")

    if suffix in SUPPORTED_TEXT_EXTENSIONS:
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("utf-8", errors="replace")
        return document_from_text(text, title=Path(filename).stem)

    return _pdf_from_bytes(filename, content)


def _pdf_from_bytes(filename: str, content: bytes) -> IngestedDocument:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise IngestError("PDF support requires pypdf. Install backend requirements first.") from exc

    reader = PdfReader(BytesIO(content))
    pages: list[str] = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")

    text = "\n\n".join(pages)
    return document_from_text(text, title=Path(filename).stem)
