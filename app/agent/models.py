from typing import Any

from pydantic import BaseModel, Field


class SqlAttempt(BaseModel):
    sql: str
    plan_summary: str = ""
    error: str | None = None


class QueryResult(BaseModel):
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    truncated: bool = False


class AgentAnswer(BaseModel):
    question: str
    answer: str
    insights: list[str] = Field(default_factory=list)
    sql: str
    attempts: list[SqlAttempt]
    result: QueryResult


class SqlRequest(BaseModel):
    sql: str


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
