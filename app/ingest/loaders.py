import io
from pathlib import Path

from pypdf import PdfReader

SUPPORTED = {".pdf", ".txt", ".md"}


class UnsupportedFileType(ValueError):
    pass


def load_pages(filename: str, data: bytes) -> list[tuple[int, str]]:
    """Return [(page_number, text)] for a file. Text files count as a single page."""
    suffix = Path(filename).suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(io.BytesIO(data))
        return [(i + 1, page.extract_text() or "") for i, page in enumerate(reader.pages)]
    if suffix in {".txt", ".md"}:
        return [(1, data.decode("utf-8", errors="replace"))]
    raise UnsupportedFileType(f"Unsupported file type: {suffix or 'unknown'}")
