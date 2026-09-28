from pydantic import BaseModel, Field

from app.platform.models import TraceStep


class IncidentRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    source: str = "default"


class AgentFinding(BaseModel):
    agent: str
    status: str
    summary: str
    trace: list[TraceStep] = Field(default_factory=list)


class IncidentAnswer(BaseModel):
    question: str
    answer: str
    findings: list[AgentFinding]
    trace: list[TraceStep] = Field(default_factory=list)
