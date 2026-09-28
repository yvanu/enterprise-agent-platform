import pytest

from app.platform import policy as policy_module
from app.platform.policy import ToolPolicy, ToolPolicyError, require_tool, tool_policies


def test_tool_policy_registry():
    policies = tool_policies()

    assert any(p.name == "readonly_sql" and p.mode == "read" for p in policies)
    assert any(p.name == "document_ingest" and p.mode == "write" for p in policies)
    assert any(
        p.name == "document_delete" and p.approval_required
        for p in policies
    )


def test_tool_policy_filter():
    assert {p.agent for p in tool_policies("ops")} == {"ops"}


def test_require_tool_blocks_unregistered_and_wrong_mode():
    assert require_tool("data", "readonly_sql", "read").risk == "low"

    with pytest.raises(ToolPolicyError):
        require_tool("data", "readonly_sql", "write")
    with pytest.raises(ToolPolicyError):
        require_tool("ops", "arbitrary_shell", "write")


def test_require_tool_blocks_pending_approval(monkeypatch):
    monkeypatch.setattr(
        policy_module,
        "POLICIES",
        [
            ToolPolicy(
                name="maintenance",
                agent="ops",
                risk="high",
                mode="write",
                approval_required=True,
            )
        ],
    )

    with pytest.raises(ToolPolicyError, match="人工审批"):
        require_tool("ops", "maintenance", "write")

    assert require_tool(
        "ops",
        "maintenance",
        "write",
        approval_granted=True,
    ).risk == "high"
