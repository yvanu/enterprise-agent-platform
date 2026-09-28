import pytest

from app.platform.approvals import (
    ApprovalCreate,
    ApprovalDecision,
    ApprovalStore,
)
from app.platform.policy import ToolPolicyError


def test_approval_lifecycle(tmp_path):
    store = ApprovalStore(str(tmp_path / "platform.db"))
    record = store.create(
        ApprovalCreate(
            agent="knowledge",
            tool="document_delete",
            target="document:7",
            reason="删除过期文档",
        ),
        requester="operator",
    )

    assert record.status == "pending"
    assert record.requested_by == "operator"

    approved = store.decide(
        record.id,
        ApprovalDecision(decision="approved"),
        actor="reviewer",
    )
    assert approved.status == "approved"
    assert approved.actor == "reviewer"

    store.consume(
        record.id,
        agent="knowledge",
        tool="document_delete",
        target="document:7",
        actor="operator",
    )
    consumed = store.get(record.id)
    assert consumed.status == "consumed"
    assert consumed.consumed_by == "operator"

    with pytest.raises(PermissionError):
        store.consume(
            record.id,
            agent="knowledge",
            tool="document_delete",
            target="document:7",
            actor="operator",
        )


def test_approval_rejects_non_approval_tool(tmp_path):
    store = ApprovalStore(str(tmp_path / "platform.db"))

    with pytest.raises(ToolPolicyError):
        store.create(
            ApprovalCreate(
                agent="data",
                tool="readonly_sql",
                target="default",
            ),
            requester="operator",
        )
