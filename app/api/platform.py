from fastapi import APIRouter, Query

from app.platform.evals import EvalResult, evaluate_runs
from app.platform.policy import ToolPolicy, tool_policies
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


@router.get("/evals", response_model=list[EvalResult])
def evals(
    limit: int = Query(50, ge=1, le=200),
    agent: str | None = Query(default=None),
) -> list[EvalResult]:
    return evaluate_runs(run_store.list(limit=limit, agent=agent))
