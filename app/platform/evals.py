from pydantic import BaseModel

from app.platform.runs import RunRecord


REQUIRED_STEPS = {
    "data": {"schema", "generate_sql", "database_query", "summarize", "presentation"},
    "knowledge": {"knowledge_search", "answer_with_context"},
    "ops": {"system_snapshot", "diagnose"},
}


class EvalCheck(BaseModel):
    name: str
    passed: bool
    detail: str = ""


class EvalResult(BaseModel):
    run_id: int
    agent: str
    passed: bool
    score: int
    checks: list[EvalCheck]


class AgentQualityMetric(BaseModel):
    agent: str
    runs: int
    success_rate: int
    avg_duration_ms: int
    eval_avg_score: int
    eval_pass_rate: int


def evaluate_run(run: RunRecord) -> EvalResult:
    names = {step.name for step in run.trace}
    required = REQUIRED_STEPS.get(run.agent, set())
    checks = [
        EvalCheck(
            name="run_status",
            passed=run.status == "ok",
            detail=run.error_type or run.status,
        ),
        EvalCheck(
            name="trace_errors",
            passed=not any(step.status == "error" for step in run.trace),
            detail=f"{sum(step.status == 'error' for step in run.trace)} error steps",
        ),
    ]
    checks.extend(
        EvalCheck(
            name=f"step:{name}",
            passed=name in names,
            detail="present" if name in names else "missing",
        )
        for name in sorted(required)
    )
    if not required:
        checks.append(
            EvalCheck(name="known_agent", passed=False, detail="no eval criteria")
        )

    passed_count = sum(check.passed for check in checks)
    score = round(passed_count / len(checks) * 100)
    return EvalResult(
        run_id=run.id,
        agent=run.agent,
        passed=all(check.passed for check in checks),
        score=score,
        checks=checks,
    )


def evaluate_runs(runs: list[RunRecord]) -> list[EvalResult]:
    return [evaluate_run(run) for run in runs]


def summarize_quality(runs: list[RunRecord]) -> list[AgentQualityMetric]:
    metrics: list[AgentQualityMetric] = []
    for agent in sorted({run.agent for run in runs}):
        agent_runs = [run for run in runs if run.agent == agent]
        evals = evaluate_runs(agent_runs)
        metrics.append(
            AgentQualityMetric(
                agent=agent,
                runs=len(agent_runs),
                success_rate=round(sum(run.status == "ok" for run in agent_runs) / len(agent_runs) * 100),
                avg_duration_ms=round(sum(run.duration_ms for run in agent_runs) / len(agent_runs)),
                eval_avg_score=round(sum(item.score for item in evals) / len(evals)),
                eval_pass_rate=round(sum(item.passed for item in evals) / len(evals) * 100),
            )
        )
    return metrics
