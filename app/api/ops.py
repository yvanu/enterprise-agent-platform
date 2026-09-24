from fastapi import APIRouter, HTTPException, Query

from app.agents.ops.agent import OpsAgent
from app.agents.ops.models import (
    DiagnoseRequest,
    LogTail,
    OpsAnswer,
    OpsSnapshot,
    PrometheusRequest,
    PrometheusResult,
)
from app.core.config import get_settings
from app.platform.llm import LLMNotConfiguredError, OpenAICompatibleLLM


router = APIRouter(prefix="/api/v1/ops", tags=["ops"])
settings = get_settings()
agent = OpsAgent(
    OpenAICompatibleLLM(settings),
    log_files=settings.ops_log_files,
    prometheus_url=settings.prometheus_url,
    http_timeout_seconds=settings.ops_http_timeout_seconds,
)


@router.get("/snapshot", response_model=OpsSnapshot)
def snapshot() -> OpsSnapshot:
    return agent.snapshot()


@router.get("/logs", response_model=list[LogTail])
def logs(lines: int = Query(80, ge=1, le=500)) -> list[LogTail]:
    return agent.logs(lines)


@router.post("/prometheus/query", response_model=PrometheusResult)
def prometheus(request: PrometheusRequest) -> PrometheusResult:
    try:
        return agent.prometheus(request.query)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/diagnose", response_model=OpsAnswer)
def diagnose(request: DiagnoseRequest) -> OpsAnswer:
    try:
        return agent.diagnose(request.question)
    except LLMNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
