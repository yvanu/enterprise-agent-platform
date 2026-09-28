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
        )
    )

    assert record.status == "pending"

    approved = store.decide(
        record.id,
        ApprovalDecision(decision="approved", actor="reviewer"),
    )
    assert approved.status == "approved"
    assert approved.actor == "reviewer"

    store.consume(
        record.id,
        agent="knowledge",
        tool="document_delete",
        target="document:7",
    )
    assert store.get(record.id).status == "consumed"

    with pytest.raises(PermissionError):
        store.consume(
            record.id,
            agent="knowledge",
            tool="document_delete",
            target="document:7",
        )


def test_approval_rejects_non_approval_tool(tmp_path):
    store = ApprovalStore(str(tmp_path / "platform.db"))

    with pytest.raises(ToolPolicyError):
        store.create(
            ApprovalCreate(
                agent="data",
                tool="readonly_sql",
                target="default",
            )
        )
