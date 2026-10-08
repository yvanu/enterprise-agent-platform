from pathlib import Path
from time import perf_counter
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse

from app.core.config import get_settings
from app.platform.approvals import (
    ApprovalCreate,
    ApprovalDecision,
    ApprovalRecord,
    approval_store,
)
from app.platform.auth import Identity, require_roles
from app.demo.incident import DemoIncidentResponse, run_demo
from app.platform.configuration import PlatformSettingsUpdate, SettingsTestRequest, apply_settings, settings_view
from app.platform.evals import AgentQualityMetric, EvalResult, evaluate_run, evaluate_runs, summarize_quality
from app.platform.llm import OpenAICompatibleLLM
from app.platform.policy import ToolPolicy, ToolPolicyError, tool_policies
from app.platform.regression import RegressionReport, run_regression_suite
from app.platform.runs import RunRecord, run_store, start_run


router = APIRouter(prefix="/api/v1/platform", tags=["platform"])
settings = get_settings()


@router.get("/tools", response_model=list[ToolPolicy])
def tools(agent: str | None = Query(default=None)) -> list[ToolPolicy]:
    return tool_policies(agent)


@router.get("/settings")
def platform_settings(
    identity: Annotated[Identity, Depends(require_roles("admin"))],
) -> dict:
    return settings_view(settings)


@router.put("/settings")
def update_platform_settings(
    request: PlatformSettingsUpdate,
    identity: Annotated[Identity, Depends(require_roles("admin"))],
) -> dict:
    try:
        changed, restart_required = apply_settings(settings, request)

        from app.api import data as data_api
        from app.api.knowledge import agent as knowledge_agent
        from app.api.ops import agent as ops_agent

        knowledge_agent.top_k = settings.knowledge_top_k
        ops_agent.log_files = [
            Path(item.strip()).resolve()
            for item in settings.ops_log_files.split(",")
            if item.strip()
        ]
        ops_agent.prometheus_url = settings.prometheus_url.rstrip("/")
        ops_agent.http_timeout_seconds = settings.ops_http_timeout_seconds
        ops_agent.enable_docker = settings.ops_enable_docker
        ops_agent.enable_kubernetes = settings.ops_enable_kubernetes
        ops_agent.allowed_services = {
            item.strip()
            for item in settings.ops_allowed_services.split(",")
            if item.strip()
        }
        ops_agent.command_timeout_seconds = settings.ops_command_timeout_seconds
        if "data_sources" in changed:
            for name in list(data_api._databases):
                if name != "default":
                    data_api._databases.pop(name, None)

        return {
            "settings": settings_view(settings),
            "changed": changed,
            "restart_required": restart_required,
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/settings/test")
def test_platform_settings(
    request: SettingsTestRequest,
    identity: Annotated[Identity, Depends(require_roles("admin"))],
) -> dict:
    llm = OpenAICompatibleLLM(settings)
    started = perf_counter()
    try:
        if request.target == "chat":
            output = llm.chat([{"role": "user", "content": "Reply with OK only."}])
            detail = output[:200]
            model = settings.llm_model
        else:
            vectors = llm.embed(["enterprise agent platform connection test"])
            dimension = len(vectors[0]) if vectors else 0
            detail = f"embedding dimension: {dimension}"
            model = settings.embedding_model
        return {
            "ok": True,
            "target": request.target,
            "model": model,
            "latency_ms": round((perf_counter() - started) * 1000),
            "detail": detail,
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"{type(exc).__name__}: {exc}") from exc


@router.get("/runs", response_model=list[RunRecord])
def runs(
    limit: int = Query(50, ge=1, le=200),
    agent: str | None = Query(default=None),
) -> list[RunRecord]:
    return run_store.list(limit=limit, agent=agent)


@router.get("/runs/{run_id}")
def run_detail(run_id: int) -> dict:
    run = run_store.get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run 不存在")
    return {"run": run, "eval": evaluate_run(run)}


@router.get("/evals", response_model=list[EvalResult])
def evals(
    limit: int = Query(50, ge=1, le=200),
    agent: str | None = Query(default=None),
) -> list[EvalResult]:
    return evaluate_runs(run_store.list(limit=limit, agent=agent))


@router.get("/metrics", response_model=list[AgentQualityMetric])
def metrics(limit: int = Query(200, ge=1, le=200)) -> list[AgentQualityMetric]:
    return summarize_quality(run_store.list(limit=limit))


@router.get("/metrics/prometheus", response_class=PlainTextResponse)
def prometheus_metrics(limit: int = Query(200, ge=1, le=200)) -> str:
    lines: list[str] = []
    for metric in summarize_quality(run_store.list(limit=limit)):
        label = f'agent="{metric.agent}"'
        lines.extend(
            [
                f'enterprise_agent_runs_total{{{label}}} {metric.runs}',
                f'enterprise_agent_success_ratio{{{label}}} {metric.success_rate / 100}',
                f'enterprise_agent_duration_ms{{{label},quantile="0.5"}} {metric.p50_duration_ms}',
                f'enterprise_agent_duration_ms{{{label},quantile="0.95"}} {metric.p95_duration_ms}',
                f'enterprise_agent_eval_score{{{label}}} {metric.eval_avg_score}',
                f'enterprise_agent_eval_pass_ratio{{{label}}} {metric.eval_pass_rate / 100}',
            ]
        )
        for error_type, count in metric.error_types.items():
            lines.append(
                f'enterprise_agent_errors_total{{{label},error_type="{error_type}"}} {count}'
            )
    return "\n".join(lines) + ("\n" if lines else "")


@router.get("/approvals", response_model=list[ApprovalRecord])
def approvals(
    identity: Annotated[Identity, Depends(require_roles("operator", "approver", "admin"))],
    limit: int = Query(50, ge=1, le=200),
) -> list[ApprovalRecord]:
    return approval_store.list(limit)


@router.post("/approvals", response_model=ApprovalRecord)
def create_approval(
    request: ApprovalCreate,
    identity: Annotated[Identity, Depends(require_roles("operator", "admin"))],
) -> ApprovalRecord:
    try:
        return approval_store.create(request, requester=identity.username)
    except (ToolPolicyError, ValueError, KeyError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/approvals/{approval_id}/decision", response_model=ApprovalRecord)
def decide_approval(
    approval_id: int,
    decision: ApprovalDecision,
    identity: Annotated[Identity, Depends(require_roles("approver", "admin"))],
) -> ApprovalRecord:
    current = approval_store.get(approval_id)
    if current is None:
        raise HTTPException(status_code=404, detail="审批记录不存在")
    if current.requested_by == identity.username and identity.role != "admin":
        raise HTTPException(status_code=409, detail="申请人不能审批自己的请求")
    try:
        return approval_store.decide(
            approval_id,
            decision,
            actor=identity.username,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/demo/incident", response_model=DemoIncidentResponse)
def demo_incident(
    identity: Annotated[Identity, Depends(require_roles("operator", "admin"))],
) -> dict:
    run = start_run("supervisor")
    try:
        answer = run_demo()
        run.success(answer.trace)
        return DemoIncidentResponse(answer=answer)
    except Exception as exc:
        run.error(exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/regression/run", response_model=RegressionReport)
def regression(
    identity: Annotated[Identity, Depends(require_roles("operator", "admin"))],
) -> RegressionReport:
    return run_regression_suite()
