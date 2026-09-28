from app.platform.evals import evaluate_run, summarize_quality
from app.platform.models import TraceStep
from app.platform.runs import RunRecord


def _run(agent: str, names: list[str], status: str = "ok") -> RunRecord:
    return RunRecord(
        id=1,
        agent=agent,
        status=status,
        duration_ms=10,
        trace=[TraceStep(kind="tool", name=name) for name in names],
        error_type="RuntimeError" if status == "error" else None,
        created_at="2026-09-28 10:00:00",
    )


def test_data_eval_passes_complete_trace():
    result = evaluate_run(
        _run(
            "data",
            ["schema", "generate_sql", "database_query", "summarize", "presentation"],
        )
    )

    assert result.passed is True
    assert result.score == 100


def test_eval_fails_missing_step_and_error_run():
    missing = evaluate_run(_run("knowledge", ["knowledge_search"]))
    failed = evaluate_run(_run("ops", [], status="error"))

    assert missing.passed is False
    assert any(check.name == "step:answer_with_context" and not check.passed for check in missing.checks)
    assert failed.passed is False


def test_supervisor_eval_passes_complete_trace():
    result = evaluate_run(
        _run(
            "supervisor",
            ["delegate_ops", "delegate_knowledge", "delegate_data", "synthesize"],
        )
    )

    assert result.passed is True
    assert result.score == 100


def test_quality_metrics_group_by_agent():
    complete = ["schema", "generate_sql", "database_query", "summarize", "presentation"]
    runs = [
        _run("data", complete),
        RunRecord(
            id=2,
            agent="data",
            status="error",
            duration_ms=30,
            trace=[],
            error_type="RuntimeError",
            created_at="2026-09-28 10:01:00",
        ),
    ]

    metric = summarize_quality(runs)[0]

    assert metric.agent == "data"
    assert metric.runs == 2
    assert metric.success_rate == 50
    assert metric.avg_duration_ms == 20
    assert metric.p50_duration_ms == 10
    assert metric.p95_duration_ms == 30
    assert metric.eval_avg_score == 57
    assert metric.eval_pass_rate == 50
    assert metric.error_types == {"RuntimeError": 1}
