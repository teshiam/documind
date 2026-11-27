from dataclasses import dataclass
from uuid import UUID

import numpy as np

from .db import pool
from .ingest.chunking import Chunk


@dataclass(frozen=True)
class Retrieved:
    content: str
    page: int
    filename: str
    score: float  # cosine similarity, higher is better


def _vec(values: list[float]) -> np.ndarray:
    return np.asarray(values, dtype=np.float32)


def add_document(filename: str, chunks: list[Chunk], embeddings: list[list[float]]) -> UUID:
    with pool.connection() as conn:
        row = conn.execute(
            "INSERT INTO documents (filename) VALUES (%s) RETURNING id", (filename,)
        ).fetchone()
        document_id = row[0]
        with conn.cursor() as cur:
            cur.executemany(
                "INSERT INTO chunks (document_id, page, chunk_index, content, embedding) "
                "VALUES (%s, %s, %s, %s, %s)",
                [
                    (document_id, c.page, c.index, c.text, _vec(e))
                    for c, e in zip(chunks, embeddings, strict=True)
                ],
            )
    return document_id


def search(query_embedding: list[float], k: int) -> list[Retrieved]:
    q = _vec(query_embedding)
    with pool.connection() as conn:
        rows = conn.execute(
            """
            SELECT c.content, c.page, d.filename, 1 - (c.embedding <=> %s) AS score
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            ORDER BY c.embedding <=> %s
            LIMIT %s
            """,
            (q, q, k),
        ).fetchall()
    return [Retrieved(content=r[0], page=r[1], filename=r[2], score=float(r[3])) for r in rows]


def list_documents() -> list[dict]:
    with pool.connection() as conn:
        rows = conn.execute(
            """
            SELECT d.id, d.filename, d.created_at, count(c.id)
            FROM documents d LEFT JOIN chunks c ON c.document_id = d.id
            GROUP BY d.id ORDER BY d.created_at DESC
            """
        ).fetchall()
    return [{"id": r[0], "filename": r[1], "created_at": r[2], "chunks": r[3]} for r in rows]


def delete_document(document_id: UUID) -> bool:
    with pool.connection() as conn:
        cur = conn.execute("DELETE FROM documents WHERE id = %s", (document_id,))
        return cur.rowcount > 0
