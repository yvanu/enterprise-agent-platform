from fastapi.testclient import TestClient

from app.api import platform as platform_api
from app.main import app
from app.platform import auth as auth_module
from app.platform.approvals import ApprovalStore
from app.platform.auth import parse_identity


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_parse_identity():
    identity = parse_identity("alice:operator")

    assert identity.username == "alice"
    assert identity.role == "operator"


def test_auth_and_rbac(monkeypatch, tmp_path):
    monkeypatch.setattr(auth_module.settings, "auth_enabled", True)
    monkeypatch.setattr(
        auth_module.settings,
        "auth_tokens",
        {
            "user-token": "alice:user",
            "operator-token": "operator:operator",
            "approver-token": "reviewer:approver",
        },
    )
    monkeypatch.setattr(
        platform_api,
        "approval_store",
        ApprovalStore(str(tmp_path / "platform.db")),
    )
    client = TestClient(app)

    assert client.get("/api/v1/platform/tools").status_code == 401
    assert client.get(
        "/api/v1/platform/tools",
        headers=_headers("user-token"),
    ).status_code == 200

    request = client.post(
        "/api/v1/platform/approvals",
        headers=_headers("operator-token"),
        json={
            "agent": "knowledge",
            "tool": "document_delete",
            "target": "document:7",
            "reason": "过期",
        },
    )
    assert request.status_code == 200
    approval = request.json()
    assert approval["requested_by"] == "operator"

    assert client.post(
        f"/api/v1/platform/approvals/{approval['id']}/decision",
        headers=_headers("operator-token"),
        json={"decision": "approved"},
    ).status_code == 403

    decision = client.post(
        f"/api/v1/platform/approvals/{approval['id']}/decision",
        headers=_headers("approver-token"),
        json={"decision": "approved"},
    )
    assert decision.status_code == 200
    assert decision.json()["actor"] == "reviewer"
