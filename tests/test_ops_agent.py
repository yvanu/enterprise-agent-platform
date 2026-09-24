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
