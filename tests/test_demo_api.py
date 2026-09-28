from fastapi.testclient import TestClient

from app.main import app
from app.platform import runs as runs_module
from app.platform.runs import RunStore


def test_offline_demo_api_records_supervisor_run(monkeypatch, tmp_path):
    store = RunStore(str(tmp_path / "platform.db"))
    monkeypatch.setattr(runs_module, "run_store", store)

    response = TestClient(app).post("/api/v1/platform/demo/incident", json={})

    assert response.status_code == 200
    payload = response.json()
    assert payload["mode"] == "offline"
    assert payload["isolated"] is True
    assert [item["status"] for item in payload["answer"]["findings"]] == [
        "ok",
        "ok",
        "ok",
    ]
    runs = store.list(agent="supervisor")
    assert len(runs) == 1
    assert runs[0].status == "ok"
    assert runs[0].trace[-1].name == "synthesize"
