from typing import Any

from pydantic import BaseModel, Field

from app.platform.models import TraceStep


class SqlAttempt(BaseModel):
    sql: str
    plan_summary: str = ""
    error: str | None = None


class QueryResult(BaseModel):
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    truncated: bool = False


class ChartSpec(BaseModel):
    type: str = "bar"
    title: str
    labels: list[str]
    values: list[float]
    x_column: str
    y_column: str


class AgentAnswer(BaseModel):
    question: str
    answer: str
    insights: list[str] = Field(default_factory=list)
    sql: str
    attempts: list[SqlAttempt]
    result: QueryResult
    chart: ChartSpec | None = None
    report_markdown: str = ""
    trace: list[TraceStep] = Field(default_factory=list)


class SqlRequest(BaseModel):
    sql: str


class AskRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
