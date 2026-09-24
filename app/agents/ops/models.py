from typing import Any

from pydantic import BaseModel, Field


class DiagnoseRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)


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
