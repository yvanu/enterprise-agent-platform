from pydantic import BaseModel, Field

from app.platform.auth import Role
from app.platform.models import TraceStep


class DocumentRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    allowed_roles: list[Role] = Field(
        default_factory=lambda: ["user", "operator", "approver", "admin"]
    )


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)


class Source(BaseModel):
    document_id: int
    title: str
    chunk_index: int
    text: str
    score: float
    version: int = 1
    tags: list[str] = Field(default_factory=list)


class KnowledgeAnswer(BaseModel):
    question: str
    answer: str
    sources: list[Source]
    trace: list[TraceStep] = Field(default_factory=list)
