import psycopg
from pgvector.psycopg import register_vector
from psycopg_pool import ConnectionPool

from .config import settings

SCHEMA = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    filename    text NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS chunks (
    id           bigserial PRIMARY KEY,
    document_id  uuid NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    page         int NOT NULL,
    chunk_index  int NOT NULL,
    content      text NOT NULL,
    embedding    vector({dim}) NOT NULL
);

CREATE INDEX IF NOT EXISTS chunks_embedding_idx
    ON chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS chunks_document_idx ON chunks (document_id);
"""


def init_db() -> None:
    """Create the extension and tables. Uses a plain connection because the vector
    type must exist before register_vector() can be called on pooled connections."""
    with psycopg.connect(settings.database_url, autocommit=True) as conn:
        conn.execute(SCHEMA.format(dim=settings.embedding_dim))


def _configure(conn: psycopg.Connection) -> None:
    register_vector(conn)


pool = ConnectionPool(settings.database_url, configure=_configure, open=False)
