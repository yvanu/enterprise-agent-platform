from fastapi import APIRouter, HTTPException, Query

from app.platform.evals import AgentQualityMetric, EvalResult, evaluate_run, evaluate_runs, summarize_quality
from app.platform.policy import ToolPolicy, tool_policies
from app.platform.regression import RegressionReport, run_regression_suite
from app.platform.runs import RunRecord, run_store


router = APIRouter(prefix="/api/v1/platform", tags=["platform"])


@router.get("/tools", response_model=list[ToolPolicy])
def tools(agent: str | None = Query(default=None)) -> list[ToolPolicy]:
    return tool_policies(agent)


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


@router.post("/regression/run", response_model=RegressionReport)
def regression() -> RegressionReport:
    return run_regression_suite()
