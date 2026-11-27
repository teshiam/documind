import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    text: str
    page: int
    index: int


def _hard_split(text: str, max_chars: int, overlap: int) -> list[str]:
    """Fallback for a single paragraph longer than max_chars."""
    step = max(1, max_chars - overlap)
    return [text[i : i + max_chars] for i in range(0, len(text), step)]


def chunk_text(text: str, max_chars: int = 1000, overlap: int = 150) -> list[str]:
    """Paragraph-aware chunking.

    Paragraphs are packed together up to max_chars. When a chunk is flushed, its tail
    (`overlap` chars) seeds the next chunk so context isn't lost at boundaries.
    Every returned chunk is <= max_chars.
    """
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    pieces: list[str] = []
    for p in paragraphs:
        pieces.extend(_hard_split(p, max_chars, overlap) if len(p) > max_chars else [p])

    chunks: list[str] = []
    buf = ""
    for piece in pieces:
        if buf and len(buf) + len(piece) + 2 > max_chars:
            chunks.append(buf)
            tail = buf[-overlap:] if overlap else ""
            if tail and len(tail) + len(piece) + 2 <= max_chars:
                buf = f"{tail}\n\n{piece}"
            else:
                buf = piece
        else:
            buf = f"{buf}\n\n{piece}" if buf else piece
    if buf:
        chunks.append(buf)
    return chunks


def chunk_pages(
    pages: list[tuple[int, str]], max_chars: int = 1000, overlap: int = 150
) -> list[Chunk]:
    """Chunk each page separately so every chunk keeps an exact page number for citations."""
    result: list[Chunk] = []
    for page_number, text in pages:
        for piece in chunk_text(text, max_chars, overlap):
            result.append(Chunk(text=piece, page=page_number, index=len(result)))
    return result
