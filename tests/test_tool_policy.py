from app.platform.policy import tool_policies


def test_tool_policy_registry():
    policies = tool_policies()

    assert any(p.name == "readonly_sql" and p.mode == "read" for p in policies)
    assert any(p.name == "document_ingest" and p.mode == "write" for p in policies)
    assert all(p.approval_required is False for p in policies)


def test_tool_policy_filter():
    assert {p.agent for p in tool_policies("ops")} == {"ops"}
