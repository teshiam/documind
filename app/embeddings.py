from functools import lru_cache

from .config import settings


@lru_cache(maxsize=1)
def _model():
    # Imported lazily so tests and tooling don't need to load the ONNX model.
    from fastembed import TextEmbedding

    return TextEmbedding(model_name=settings.embedding_model)


def embed_texts(texts: list[str]) -> list[list[float]]:
    return [vec.tolist() for vec in _model().embed(texts)]


def embed_query(query: str) -> list[float]:
    return next(iter(_model().query_embed(query))).tolist()
