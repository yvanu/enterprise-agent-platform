from scripts.demo_incident import run_demo


def test_offline_incident_demo():
    result = run_demo()

    assert all(item.status == "ok" for item in result.findings)
    assert [item.agent for item in result.findings] == ["ops", "knowledge", "data"]
    assert "上游依赖超时" in result.answer
    assert [step.name for step in result.trace] == [
        "delegate_ops",
        "delegate_knowledge",
        "delegate_data",
        "synthesize",
    ]
