from app.ingest.chunking import chunk_pages, chunk_text


def test_short_text_is_single_chunk():
    assert chunk_text("Hello world.", max_chars=100, overlap=10) == ["Hello world."]


def test_empty_text_returns_no_chunks():
    assert chunk_text("   \n\n  ", max_chars=100, overlap=10) == []


def test_chunks_never_exceed_max_chars():
    text = "\n\n".join(f"Paragraph {i}. " + "word " * 40 for i in range(30))
    chunks = chunk_text(text, max_chars=300, overlap=50)
    assert len(chunks) > 1
    assert all(len(c) <= 300 for c in chunks)


def test_long_paragraph_is_hard_split():
    chunks = chunk_text("x" * 2500, max_chars=1000, overlap=100)
    assert len(chunks) >= 3
    assert all(len(c) <= 1000 for c in chunks)


def test_overlap_carries_context_between_chunks():
    paras = [f"Section {i}: " + ("alpha " * 30).strip() for i in range(6)]
    chunks = chunk_text("\n\n".join(paras), max_chars=400, overlap=80)
    assert len(chunks) > 1
    assert chunks[0][-40:] in chunks[1]


def test_chunk_pages_preserves_page_numbers_and_indexes():
    pages = [(1, "First page text."), (2, ""), (3, "Third page text.")]
    chunks = chunk_pages(pages, max_chars=100, overlap=10)
    assert [(c.page, c.index) for c in chunks] == [(1, 0), (3, 1)]
