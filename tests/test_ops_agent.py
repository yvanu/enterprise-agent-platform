from app.agents.ops.agent import OpsAgent


class _NoopLLM:
    pass


def test_snapshot_is_readonly_system_data():
    snapshot = OpsAgent(_NoopLLM()).snapshot()

    assert snapshot.cpu_count is None or snapshot.cpu_count > 0
    assert snapshot.disk["total"] > 0
    assert snapshot.disk["free"] >= 0
