import json

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.modules.agents import service as agent_module
from app.modules.agents import runtime as runtime_module
from app.modules.agents.base import Base
from app.modules.agents.models import AgentCreate
from app.modules.agents.service import agent_service
from app.modules.tools import mcp_service as mcp_module
from app.modules.tools import service as tool_module
from app.modules.tools.service import tool_service
from app.platform.approvals import ApprovalCreate, ApprovalDecision, ApprovalStore


@pytest.fixture()
def mcp_environment(monkeypatch, tmp_path):
    url = "https://tools.test/mcp"
    monkeypatch.setattr(mcp_module.get_settings(), "mcp_allowed_urls", url)
    engine = create_engine(f"sqlite:///{tmp_path / 'mcp.db'}",
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    monkeypatch.setattr(agent_module, "SessionLocal", factory)
    monkeypatch.setattr(tool_module, "SessionLocal", factory)
    monkeypatch.setattr(mcp_module, "SessionLocal", factory)
    agent_service.seed_built_ins()
    tool_service.seed_builtin_tools()
    tool_service.seed_builtin_assignments()

    approvals = ApprovalStore(str(tmp_path / "approvals.db"))
    monkeypatch.setattr(mcp_module, "approval_store", approvals)
    import app.api.platform as platform_module
    monkeypatch.setattr(platform_module, "approval_store", approvals)

    calls = []
    remote = {"tools": [
        {"name": "lookup", "description": "Lookup public information",
         "inputSchema": {"type": "object", "properties": {"q": {"type": "string"}}},
         "annotations": {"readOnlyHint": True}},
        {"name": "danger", "inputSchema": {"type": "object"},
         "annotations": {"readOnlyHint": True}},
    ]}

    def mock_handler(request):
        payload = json.loads(request.content)
        calls.append(payload)
        method = payload["method"]
        if method == "notifications/initialized":
            return httpx.Response(202)
        if method == "initialize":
            return httpx.Response(
                200, json={"jsonrpc": "2.0", "id": 1,
                           "result": {"protocolVersion": "2025-03-26",
                                      "capabilities": {"tools": {}}}},
                headers={"Mcp-Session-Id": "test-session"})
        if method == "tools/list":
            response = {"jsonrpc": "2.0", "id": payload["id"], "result": remote}
            return httpx.Response(200, text="event: message\ndata: " +
                                  json.dumps(response) + "\n\n",
                                  headers={"Content-Type": "text/event-stream"})
        if method == "tools/call":
            assert request.headers["mcp-session-id"] == "test-session"
            return httpx.Response(200, json={
                "jsonrpc": "2.0", "id": payload["id"],
                "result": {"content": [{"type": "text", "text": "ok"}]}})
        raise AssertionError(f"Unexpected MCP method: {method}")

    transport = httpx.MockTransport(mock_handler)
    monkeypatch.setattr(mcp_module.MCPClient, "_client",
                        lambda self: httpx.Client(transport=transport, trust_env=False))
    return TestClient(app), approvals, remote, calls, url


def test_mcp_discover_assign_approve_invoke(mcp_environment):
    client, approvals, remote, calls, url = mcp_environment

    denied_url = client.post("/api/v1/mcp/servers",
                             json={"name": "bad", "url": "http://127.0.0.1/admin"})
    assert denied_url.status_code == 400
    assert not calls

    created = client.post("/api/v1/mcp/servers",
                          json={"name": "Demo", "url": url})
    assert created.status_code == 201
    server_id = created.json()["id"]
    discovery = client.post(f"/api/v1/mcp/servers/{server_id}/discover")
    assert discovery.status_code == 200, discovery.text
    tools = {item["name"]: item for item in discovery.json()}
    assert len(tools) == 2
    assert all(item["provider"] == "mcp" and item["mode"] == "write"
               and item["risk"] == "high" and item["approval_required"]
               for item in tools.values())

    agent_id = agent_service.create(AgentCreate(name="MCP agent"),
                                    actor="admin").id
    agent_service.publish(agent_id, 1)
    tool = tools["lookup"]
    endpoint = f"/api/v1/agents/{agent_id}/tools/{tool['id']}/invoke"
    args = {"arguments": {"q": "hello"}}

    unassigned = client.post(endpoint, json=args)
    assert unassigned.status_code == 403
    assert "未分配" in str(unassigned.json())

    agent_service.create_version(agent_id, agent_module.AgentVersionPatch(), actor="admin")
    tool_service.replace_version_tools(agent_id, 2, [tool["id"]])
    agent_service.publish(agent_id, 2)

    no_approval = client.post(endpoint, json=args)
    assert no_approval.status_code == 403
    assert "人工审批" in str(no_approval.json())
    assert not any(x["method"] == "tools/call" for x in calls)

    approval = approvals.create(
        ApprovalCreate(agent=tool["namespace"], tool="lookup",
                       target=f"tool:{tool['id']}", arguments={"q": "hello"},
                       agent_id=agent_id, agent_version=2), requester="operator")
    approvals.decide(approval.id, ApprovalDecision(decision="approved"), actor="admin")
    invoked = client.post(endpoint, json={**args, "approval_id": approval.id})
    assert invoked.status_code == 200, invoked.text
    assert invoked.json()["result"]["content"][0]["text"] == "ok"
    assert invoked.json()["run_id"] > 0
    assert approvals.get(approval.id).status == "consumed"

    replay = client.post(endpoint, json={**args, "approval_id": approval.id})
    assert replay.status_code == 403
    assert len([x for x in calls if x["method"] == "tools/call"]) == 1

    remote["tools"] = [remote["tools"][0]]
    refresh = client.post(f"/api/v1/mcp/servers/{server_id}/discover")
    assert refresh.status_code == 200
    assert len(refresh.json()) == 1
    assert tool_service.get(tools["danger"]["id"]).enabled is False


def test_mcp_failed_discovery_does_not_import_partial_registry(mcp_environment):
    client, _, remote, _, url = mcp_environment
    server_id = client.post("/api/v1/mcp/servers",
                            json={"name": "Demo", "url": url}).json()["id"]
    remote["tools"].append(remote["tools"][0])
    response = client.post(f"/api/v1/mcp/servers/{server_id}/discover")
    assert response.status_code == 400
    assert not any(item.provider == "mcp" for item in tool_service.list())


def test_generic_agent_uses_only_published_approved_mcp_tools(mcp_environment, monkeypatch):
    client, approvals, _, calls, url = mcp_environment
    server_id = client.post("/api/v1/mcp/servers",
                            json={"name": "Demo", "url": url}).json()["id"]
    tools = client.post(f"/api/v1/mcp/servers/{server_id}/discover").json()
    lookup = next(tool for tool in tools if tool["name"] == "lookup")

    class FakeToolLLM:
        def __init__(self, settings):
            pass

        def chat_with_tools(self, messages, definitions, **kwargs):
            assert len(definitions) == 1
            assert definitions[0]["function"]["name"] == "mcp_" + lookup["id"].replace("-", "_")
            if messages[-1]["role"] == "tool":
                assert "ok" in messages[-1]["content"]
                return {"content": "Used trusted lookup."}
            return {"content": None, "tool_calls": [{
                "id": "call-1", "type": "function",
                "function": {"name": definitions[0]["function"]["name"],
                             "arguments": '{"q":"hello"}'}
            }]}

        def chat(self, messages, **kwargs):
            return "No MCP tool was offered."

    monkeypatch.setattr(runtime_module, "OpenAICompatibleLLM", FakeToolLLM)
    agent_id = agent_service.create(AgentCreate(name="MCP planning agent"),
                                    actor="development").id
    agent_service.publish(agent_id, 1)
    agent_service.create_version(agent_id, agent_module.AgentVersionPatch(), actor="development")
    tool_service.replace_version_tools(agent_id, 2, [lookup["id"]])
    agent_service.publish(agent_id, 2)
    endpoint = f"/api/v1/agents/{agent_id}/run"

    denied = client.post(endpoint, json={"input": "run lookup"})
    assert denied.status_code == 200
    assert denied.json()["pending_tools"][0]["arguments"] == {"q": "hello"}
    assert not any(x["method"] == "tools/call" for x in calls)

    approval = approvals.create(
        ApprovalCreate(agent=lookup["namespace"], tool=lookup["name"],
                       target=f"tool:{lookup['id']}", arguments={"q": "hello"},
                       agent_id=agent_id, agent_version=2), requester="development")
    approvals.decide(approval.id, ApprovalDecision(decision="approved"), actor="admin")
    request = {"input": "run lookup", "approval_ids": {lookup["id"]: approval.id}}
    success = client.post(endpoint, json=request)
    assert success.status_code == 200, success.text
    assert success.json()["answer"] == "Used trusted lookup."
    assert any(item["kind"] == "tool" and item["name"] == lookup["key"]
               for item in success.json()["trace"])
    assert len([x for x in calls if x["method"] == "tools/call"]) == 1
    assert approvals.get(approval.id).status == "consumed"

    replay = client.post(endpoint, json=request)
    assert replay.status_code == 403
    assert len([x for x in calls if x["method"] == "tools/call"]) == 1

    # A different Agent cannot gain this tool from model instructions alone.
    outsider = agent_service.create(AgentCreate(name="No tools"), actor="development")
    agent_service.publish(outsider.id, 1)
    no_tools = client.post(f"/api/v1/agents/{outsider.id}/run",
                           json={"input": "run lookup", "approval_ids": request["approval_ids"]})
    assert no_tools.status_code == 200
    assert no_tools.json()["answer"] == "No MCP tool was offered."


def test_generic_agent_rejects_unassigned_tool_in_batch_before_execution(mcp_environment, monkeypatch):
    client, approvals, _, calls, url = mcp_environment
    server_id = client.post("/api/v1/mcp/servers",
                            json={"name": "Demo", "url": url}).json()["id"]
    tool = client.post(f"/api/v1/mcp/servers/{server_id}/discover").json()[0]
    agent_id = agent_service.create(AgentCreate(name="Safe agent"),
                                    actor="development").id
    agent_service.publish(agent_id, 1)
    agent_service.create_version(agent_id, agent_module.AgentVersionPatch(), actor="development")
    tool_service.replace_version_tools(agent_id, 2, [tool["id"]])
    agent_service.publish(agent_id, 2)
    approval = approvals.create(
        ApprovalCreate(agent=tool["namespace"], tool=tool["name"],
                       target=f"tool:{tool['id']}", arguments={},
                       agent_id=agent_id, agent_version=2), requester="development")
    approvals.decide(approval.id, ApprovalDecision(decision="approved"), actor="admin")

    class MaliciousLLM:
        def __init__(self, settings):
            pass

        def chat_with_tools(self, messages, definitions, **kwargs):
            return {"tool_calls": [
                {"type": "function", "id": "valid",
                 "function": {"name": definitions[0]["function"]["name"], "arguments": "{}"}},
                {"type": "function", "id": "invalid",
                 "function": {"name": "not_assigned", "arguments": "{}"}},
            ]}

    monkeypatch.setattr(runtime_module, "OpenAICompatibleLLM", MaliciousLLM)
    response = client.post(f"/api/v1/agents/{agent_id}/run", json={
        "input": "Try to invoke an unassigned tool",
        "approval_ids": {tool["id"]: approval.id},
    })
    assert response.status_code == 403
    assert approvals.get(approval.id).status == "approved"
    assert not any(x["method"] == "tools/call" for x in calls)


def test_mcp_approval_freezes_arguments_and_agent_version(mcp_environment):
    client, approvals, _, calls, url = mcp_environment
    server_id = client.post("/api/v1/mcp/servers",
                            json={"name": "Demo", "url": url}).json()["id"]
    tool = client.post(f"/api/v1/mcp/servers/{server_id}/discover").json()[0]
    agent_id = agent_service.create(AgentCreate(name="Bound MCP agent"),
                                    actor="operator").id
    agent_service.publish(agent_id, 1)
    agent_service.create_version(agent_id, agent_module.AgentVersionPatch(), actor="operator")
    tool_service.replace_version_tools(agent_id, 2, [tool["id"]])
    agent_service.publish(agent_id, 2)
    invoke = f"/api/v1/agents/{agent_id}/tools/{tool['id']}/invoke"

    missing = client.post("/api/v1/platform/approvals", json={
        "agent": tool["namespace"], "tool": tool["name"],
        "target": f"tool:{tool['id']}"})
    assert missing.status_code == 400

    created = client.post("/api/v1/platform/approvals", json={
        "agent": tool["namespace"], "tool": tool["name"],
        "target": f"tool:{tool['id']}", "arguments": {"q": "hello"},
        "agent_id": agent_id, "agent_version": 2})
    assert created.status_code == 200, created.text
    record_id = created.json()["id"]
    assert created.json()["arguments"] == {"q": "hello"}
    assert client.post(f"/api/v1/platform/approvals/{record_id}/decision",
                       json={"decision": "approved"}).status_code == 200

    changed = client.post(invoke, json={"approval_id": record_id, "arguments": {"q": "delete"}})
    assert changed.status_code == 403
    assert approvals.get(record_id).status == "approved"
    assert not any(c["method"] == "tools/call" for c in calls)

    other = agent_service.create(AgentCreate(name="Second MCP agent"), actor="operator")
    agent_service.publish(other.id, 1)
    agent_service.create_version(other.id, agent_module.AgentVersionPatch(), actor="operator")
    tool_service.replace_version_tools(other.id, 2, [tool["id"]])
    agent_service.publish(other.id, 2)
    cross_agent = client.post(
        f"/api/v1/agents/{other.id}/tools/{tool['id']}/invoke",
        json={"approval_id": record_id, "arguments": {"q": "hello"}})
    assert cross_agent.status_code == 403

    agent_service.create_version(agent_id, agent_module.AgentVersionPatch(), actor="operator")
    agent_service.publish(agent_id, 3)
    version_changed = client.post(invoke, json={"approval_id": record_id, "arguments": {"q": "hello"}})
    assert version_changed.status_code == 403
    assert approvals.get(record_id).status == "approved"
    assert not any(c["method"] == "tools/call" for c in calls)

    agent_service.publish(agent_id, 2)
    success = client.post(invoke, json={"approval_id": record_id, "arguments": {"q": "hello"}})
    assert success.status_code == 200, success.text
    assert approvals.get(record_id).status == "consumed"
    assert len([c for c in calls if c["method"] == "tools/call"]) == 1


def test_mcp_proposal_approval_and_deterministic_resume(mcp_environment, monkeypatch):
    client, approvals, _, calls, url = mcp_environment
    server_id = client.post("/api/v1/mcp/servers",
                            json={"name": "Demo", "url": url}).json()["id"]
    tool = client.post(f"/api/v1/mcp/servers/{server_id}/discover").json()[0]
    agent_id = agent_service.create(AgentCreate(name="Resume MCP agent"), actor="operator").id
    agent_service.publish(agent_id, 1)
    agent_service.create_version(agent_id, agent_module.AgentVersionPatch(), actor="operator")
    tool_service.replace_version_tools(agent_id, 2, [tool["id"]])
    agent_service.publish(agent_id, 2)

    class Model:
        def __init__(self, settings): pass
        def chat_with_tools(self, messages, definitions, **kwargs):
            return {"tool_calls": [{
                "id": "candidate", "type": "function",
                "function": {"name": definitions[0]["function"]["name"],
                             "arguments": '{"q":"hello"}'}}]}
        def chat(self, messages, **kwargs):
            return "Summarized approved result"

    monkeypatch.setattr(runtime_module, "OpenAICompatibleLLM", Model)
    proposed = client.post(f"/api/v1/agents/{agent_id}/run", json={"input": "Summarize lookup"})
    assert proposed.status_code == 200, proposed.text
    assert proposed.json()["pending_tools"][0]["arguments"] == {"q": "hello"}
    from app.platform.runs import run_store
    assert run_store.get(proposed.json()["run_id"]).status == "waiting_approval"
    assert not any(c["method"] == "tools/call" for c in calls)

    approval_data = proposed.json()["pending_tools"][0]
    create = client.post("/api/v1/platform/approvals", json={
        "agent": approval_data["namespace"], "tool": approval_data["tool"],
        "target": "tool:" + approval_data["tool_id"],
        "arguments": approval_data["arguments"],
        "agent_id": agent_id, "agent_version": 2})
    assert create.status_code == 200, create.text
    record_id = create.json()["id"]
    resume_url = f"/api/v1/agents/{agent_id}/approvals/{record_id}/resume"
    assert client.post(resume_url, json={"input": "Summarize lookup"}).status_code == 403
    assert not any(c["method"] == "tools/call" for c in calls)
    assert client.post(f"/api/v1/platform/approvals/{record_id}/decision",
                       json={"decision": "approved"}).status_code == 200
    result = client.post(resume_url, json={"input": "Summarize lookup"})
    assert result.status_code == 200, result.text
    assert result.json()["answer"] == "Summarized approved result"
    assert result.json()["raw"]["result"]["content"][0]["text"] == "ok"
    assert approvals.get(record_id).status == "consumed"
    assert len([c for c in calls if c["method"] == "tools/call"]) == 1
    assert client.post(resume_url, json={"input": "Summarize lookup"}).status_code == 403
    assert len([c for c in calls if c["method"] == "tools/call"]) == 1
