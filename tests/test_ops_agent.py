from app.agents.ops import agent as ops_module
from app.agents.ops.agent import OpsAgent


class _NoopLLM:
    def chat(self, messages):
        return "未发现明显资源异常。"


def test_snapshot_is_readonly_system_data():
    snapshot = OpsAgent(_NoopLLM()).snapshot()

    assert snapshot.cpu_count is None or snapshot.cpu_count > 0
    assert snapshot.disk["total"] > 0
    assert snapshot.disk["free"] >= 0


def test_diagnose_returns_trace():
    answer = OpsAgent(_NoopLLM()).diagnose("服务器是否异常？")

    assert [step.name for step in answer.trace] == ["system_snapshot", "diagnose"]


def test_logs_only_read_configured_files(tmp_path):
    log = tmp_path / "app.log"
    log.write_text("one\ntwo\nthree\n", encoding="utf-8")

    result = OpsAgent(_NoopLLM(), log_files=str(log)).logs(lines=2)

    assert result[0].lines == ["two", "three"]


def test_docker_inventory(monkeypatch):
    class _Result:
        stdout = '{"Names":"api","Status":"Up 2 hours"}\n'

    monkeypatch.setattr(ops_module.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(ops_module.subprocess, "run", lambda *args, **kwargs: _Result())

    result = OpsAgent(_NoopLLM(), enable_docker=True).docker_containers()

    assert result.tool == "docker"
    assert result.items[0]["Names"] == "api"


def test_kubernetes_inventory(monkeypatch):
    class _Result:
        stdout = '{"items":[{"metadata":{"namespace":"prod","name":"api-1"},"status":{"phase":"Running","podIP":"10.0.0.2"}}]}'

    monkeypatch.setattr(ops_module.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(ops_module.subprocess, "run", lambda *args, **kwargs: _Result())

    result = OpsAgent(_NoopLLM(), enable_kubernetes=True).kubernetes_pods()

    assert result.tool == "kubernetes"
    assert result.items[0]["namespace"] == "prod"
    assert result.items[0]["phase"] == "Running"


def test_prometheus_query(monkeypatch):
    class _Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"status": "success", "data": {"result": [{"metric": {"job": "api"}, "value": [1, "1"]}]}}

    monkeypatch.setattr(ops_module.httpx, "get", lambda *args, **kwargs: _Response())
    result = OpsAgent(_NoopLLM(), prometheus_url="http://prometheus:9090").prometheus("up")

    assert result.query == "up"
    assert result.result[0]["metric"]["job"] == "api"
