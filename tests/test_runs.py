from app.platform.models import TraceStep
from app.platform.runs import RunStore


def test_run_store_records_and_filters(tmp_path):
    store = RunStore(str(tmp_path / "platform.db"))
    store.record(
        agent="data",
        status="ok",
        duration_ms=12,
        trace=[TraceStep(kind="tool", name="schema")],
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
    assert store.get(99999) is None
