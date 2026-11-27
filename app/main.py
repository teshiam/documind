import json
from collections.abc import Iterator
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from . import rag, store
from .config import settings
from .db import init_db, pool
from .embeddings import embed_query, embed_texts
from .ingest.chunking import chunk_pages
from .ingest.loaders import UnsupportedFileType, load_pages
from .schemas import AskRequest, DocumentOut, SourceOut


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    pool.open()
    yield
    pool.close()


app = FastAPI(title="DocuMind", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    free_mode = settings.llm_provider == "extractive"
    return {
        "status": "ok",
        "llm_provider": settings.llm_provider,
        "llm_model": "" if free_mode else settings.llm_model,
    }


@app.post("/documents", response_model=DocumentOut, status_code=201)
def upload_document(file: UploadFile) -> DocumentOut:
    data = file.file.read()
    if len(data) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"File exceeds {settings.max_upload_mb} MB limit")

    filename = file.filename or "untitled"
    try:
        pages = load_pages(filename, data)
    except UnsupportedFileType as exc:
        raise HTTPException(415, str(exc)) from exc

    chunks = chunk_pages(pages, settings.chunk_max_chars, settings.chunk_overlap)
    if not chunks:
        raise HTTPException(422, "No extractable text found (scanned PDFs need OCR).")

    embeddings = embed_texts([c.text for c in chunks])
    document_id = store.add_document(filename, chunks, embeddings)
    return DocumentOut(id=document_id, filename=filename, chunks=len(chunks))


@app.get("/documents", response_model=list[DocumentOut])
def get_documents() -> list[dict]:
    return store.list_documents()


@app.delete("/documents/{document_id}", status_code=204)
def remove_document(document_id: UUID) -> None:
    if not store.delete_document(document_id):
        raise HTTPException(404, "Document not found")


def _sse(event: str, data: object) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.post("/ask")
def ask(req: AskRequest) -> StreamingResponse:
    """Server-sent events: one `sources` event, many `token` events, then `done`."""
    k = req.top_k or settings.top_k
    retrieved = rag.filter_relevant(store.search(embed_query(req.question), k))
    sources = [
        SourceOut(
            n=i,
            filename=c.filename,
            page=c.page,
            score=round(c.score, 3),
            snippet=c.content[:240],
        ).model_dump()
        for i, c in enumerate(retrieved, start=1)
    ]

    def events() -> Iterator[str]:
        yield _sse("sources", sources)
        try:
            for token in rag.stream_answer(req.question, retrieved):
                yield _sse("token", token)
        except Exception as exc:  # surface LLM errors to the client instead of a dead stream
            yield _sse("error", str(exc))
        yield _sse("done", {})

    return StreamingResponse(events(), media_type="text/event-stream")
