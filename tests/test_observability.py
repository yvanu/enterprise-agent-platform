from fastapi.testclient import TestClient

from app.api import platform as platform_api
from app.main import app
from app.platform.models import TraceStep
from app.platform.runs import RunStore


def test_prometheus_metrics_endpoint(monkeypatch, tmp_path):
    store = RunStore(str(tmp_path / "platform.db"))
    store.record(
        agent="data",
        status="ok",
        duration_ms=10,
        trace=[
            TraceStep(kind="tool", name="schema"),
            TraceStep(kind="llm", name="generate_sql"),
            TraceStep(kind="tool", name="database_query"),
            TraceStep(kind="llm", name="summarize"),
            TraceStep(kind="tool", name="presentation"),
        ],
    )
    store.record(
        agent="data",
        status="error",
        duration_ms=30,
        error_type="RuntimeError",
    )
    monkeypatch.setattr(platform_api, "run_store", store)

    response = TestClient(app).get("/api/v1/platform/metrics/prometheus")

    assert response.status_code == 200
    assert 'enterprise_agent_runs_total{agent="data"} 2' in response.text
    assert 'quantile="0.95"} 30' in response.text
    assert 'error_type="RuntimeError"} 1' in response.text
