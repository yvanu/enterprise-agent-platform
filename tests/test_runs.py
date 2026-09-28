import sqlite3

from app.platform.models import TraceStep
from app.platform.runs import RunStore


def test_run_store_records_and_filters(tmp_path):
    store = RunStore(str(tmp_path / "platform.db"))
    store.record(
        agent="data",
        status="ok",
        duration_ms=12,
        trace=[TraceStep(kind="tool", name="schema")],
        request_id="req-1",
        correlation_id="corr-1",
    )
    store.record(
        agent="ops",
        status="error",
        duration_ms=8,
        error_type="RuntimeError",
    )

    runs = store.list()
    assert [run.agent for run in runs] == ["ops", "data"]
    assert runs[0].error_type == "RuntimeError"
    assert runs[1].trace[0].name == "schema"
    assert [run.agent for run in store.list(agent="data")] == ["data"]
    data_run = store.get(runs[1].id)
    assert data_run is not None
    assert data_run.trace[0].name == "schema"
    assert data_run.request_id == "req-1"
    assert data_run.correlation_id == "corr-1"
    assert store.get(99999) is None


def test_run_store_migrates_request_context_columns(tmp_path):
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE agent_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                agent TEXT NOT NULL,
                status TEXT NOT NULL,
                duration_ms INTEGER NOT NULL,
                trace_json TEXT NOT NULL,
                error_type TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    store = RunStore(str(path))
    run_id = store.record(
        agent="data",
        status="ok",
        duration_ms=1,
        request_id="req-legacy",
        correlation_id="corr-legacy",
    )

    run = store.get(run_id)
    assert run is not None
    assert run.request_id == "req-legacy"
    assert run.correlation_id == "corr-legacy"
