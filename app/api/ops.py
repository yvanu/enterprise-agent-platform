from fastapi import APIRouter, HTTPException, Query

from app.agents.ops.agent import OpsAgent
from app.agents.ops.models import (
    DiagnoseRequest,
    LogTail,
    OpsAnswer,
    OpsSnapshot,
    PrometheusRequest,
    PrometheusResult,
    RuntimeInventory,
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
    enable_docker=settings.ops_enable_docker,
    enable_kubernetes=settings.ops_enable_kubernetes,
    command_timeout_seconds=settings.ops_command_timeout_seconds,
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


@router.get("/docker", response_model=RuntimeInventory)
def docker() -> RuntimeInventory:
    try:
        return agent.docker_containers()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/kubernetes", response_model=RuntimeInventory)
def kubernetes() -> RuntimeInventory:
    try:
        return agent.kubernetes_pods()
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
