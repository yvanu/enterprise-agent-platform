from typing import Any

from pydantic import BaseModel, Field

from app.platform.models import TraceStep


class DiagnoseRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)


class PrometheusRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)


class LogTail(BaseModel):
    path: str
    lines: list[str]


class PrometheusResult(BaseModel):
    query: str
    result: list[dict[str, Any]]


class OpsSnapshot(BaseModel):
    hostname: str
    cpu_count: int | None
    load_average: tuple[float, float, float] | None
    memory: dict[str, int]
    disk: dict[str, int]


class OpsAnswer(BaseModel):
    question: str
    answer: str
    snapshot: OpsSnapshot
    logs: list[LogTail] = Field(default_factory=list)
    prometheus: PrometheusResult | None = None
    trace: list[TraceStep] = Field(default_factory=list)
