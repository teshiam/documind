from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentOut(BaseModel):
    id: UUID
    filename: str
    chunks: int
    created_at: datetime | None = None


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    top_k: int | None = Field(default=None, ge=1, le=20)


class SourceOut(BaseModel):
    n: int
    filename: str
    page: int
    score: float
    snippet: str
