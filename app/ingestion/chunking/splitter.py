import re
from typing import List

import logfire

_DOC_ID = re.compile(r"Document ID:\s*([A-Z]+-[A-Z]+-\d+)")


def _doc_header(text: str) -> str:
    """Build a '[HR-POL-08] TITLE' header from the top of the document, or '' if none."""
    m = _DOC_ID.search(text[:600])
    if not m:
        return ""
    title = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    return f"[{m.group(1)}] {title}"


def chunk_text(text: str, chunk_size: int = 1500) -> List[str]:
    """
    Simple semantic-ish chunker that splits by paragraphs.
    Ensures chunks do not exceed the specified size.
    If the document has a 'Document ID', every chunk is prefixed with it so
    answers can cite the right policy even when a chunk starts mid-document.
    """
    with logfire.span("✂️ Text Chunking", text_length=len(text)):
        if not text.strip():
            return []

        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = ""

        for p in paragraphs:
            if len(current_chunk) + len(p) < chunk_size:
                current_chunk += p + "\n\n"
            else:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = p + "\n\n"

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        valid_chunks = [c for c in chunks if c.strip()]

        header = _doc_header(text)
        if header:
            valid_chunks = [
                c if c.startswith(header) or c.startswith(header.split("] ", 1)[1])
                else f"{header}\n{c}"
                for c in valid_chunks
            ]

        logfire.info(f"✅ Generated {len(valid_chunks)} chunks")
        return valid_chunks