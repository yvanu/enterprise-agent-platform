from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.agents.ops.agent import OpsAgent
from app.agents.ops.models import (
    DiagnoseRequest,
    LogTail,
    OpsAnswer,
    OpsSnapshot,
    PrometheusRequest,
    PrometheusResult,
    RuntimeInventory,
    ServiceActionResult,
)
from app.core.config import get_settings
from app.platform.approvals import approval_store
from app.platform.auth import Identity, require_roles
from app.platform.llm import LLMNotConfiguredError, OpenAICompatibleLLM
from app.platform.policy import builtin_tool_execution_context
from app.platform.runs import start_run


router = APIRouter(
    prefix="/api/v1/ops",
    tags=["ops"],
    dependencies=[Depends(require_roles("operator", "admin"))],
)
settings = get_settings()
agent = OpsAgent(
    OpenAICompatibleLLM(settings),
    log_files=settings.ops_log_files,
    prometheus_url=settings.prometheus_url,
    http_timeout_seconds=settings.ops_http_timeout_seconds,
    enable_docker=settings.ops_enable_docker,
    enable_kubernetes=settings.ops_enable_kubernetes,
    allowed_services=settings.ops_allowed_services,
    command_timeout_seconds=settings.ops_command_timeout_seconds,
)


@router.get("/snapshot", response_model=OpsSnapshot)
def snapshot() -> OpsSnapshot:
    with builtin_tool_execution_context("ops"):
        return agent.snapshot()


@router.get("/logs", response_model=list[LogTail])
def logs(lines: int = Query(80, ge=1, le=500)) -> list[LogTail]:
    with builtin_tool_execution_context("ops"):
        return agent.logs(lines)


@router.post("/prometheus/query", response_model=PrometheusResult)
def prometheus(request: PrometheusRequest) -> PrometheusResult:
    try:
        with builtin_tool_execution_context("ops"):
            return agent.prometheus(request.query)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/docker", response_model=RuntimeInventory)
def docker() -> RuntimeInventory:
    try:
        with builtin_tool_execution_context("ops"):
            return agent.docker_containers()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/kubernetes", response_model=RuntimeInventory)
def kubernetes() -> RuntimeInventory:
    try:
        with builtin_tool_execution_context("ops"):
            return agent.kubernetes_pods()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/services/{service}/restart", response_model=ServiceActionResult)
def restart_service(
    service: str,
    approval_id: int,
    identity: Annotated[Identity, Depends(require_roles("operator", "admin"))],
) -> ServiceActionResult:
    try:
        if service not in agent.allowed_services:
            raise HTTPException(status_code=400, detail="服务不在 OPS_ALLOWED_SERVICES 白名单中")
        approval_store.consume(
            approval_id,
            agent="ops",
            tool="service_restart",
            target=f"service:{service}",
            actor=identity.username,
        )
        with builtin_tool_execution_context("ops"):
            return agent.restart_service(service, approved=True)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/diagnose", response_model=OpsAnswer)
def diagnose(request: DiagnoseRequest) -> OpsAnswer:
    run = start_run("ops")
    try:
        with builtin_tool_execution_context("ops"):
            answer = agent.diagnose(request.question)
        run.success(answer.trace)
        return answer
    except LLMNotConfiguredError as exc:
        run.error(exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        run.error(exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
