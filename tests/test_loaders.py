import pytest

from app.ingest.loaders import UnsupportedFileType, load_pages


def test_loads_text_file_as_single_page():
    assert load_pages("notes.txt", b"hello") == [(1, "hello")]


def test_loads_markdown_with_bad_bytes():
    pages = load_pages("README.md", b"ok \xff done")
    assert pages[0][0] == 1
    assert "ok" in pages[0][1]


def test_rejects_unsupported_type():
    with pytest.raises(UnsupportedFileType):
        load_pages("image.png", b"...")
