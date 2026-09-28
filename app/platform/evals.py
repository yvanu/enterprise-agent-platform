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
