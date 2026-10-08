import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.modules.agents import service as agent_module
from app.modules.agents import runtime as runtime_module
from app.modules.agents.base import Base
from app.modules.agents.models import AgentCreate, AgentVersionPatch
from app.modules.agents.service import agent_service
from app.modules.tools import service as tool_module
from app.modules.tools import openapi_service as openapi_module
from app.modules.tools.openapi_service import _parse_operations
from app.modules.tools.service import tool_service
from app.platform.approvals import ApprovalStore


DOCUMENT = {
    "openapi": "3.0.3", "info": {"title": "Inventory", "version": "1"},
    "servers": [{"url": "http://127.0.0.1:1"}],  # Ignored: never use spec-supplied servers.
    "paths": {
        "/items/{item_id}": {
            "get": {
                "operationId": "get_item", "summary": "Fetch an item",
                "parameters": [
                    {"name": "item_id", "in": "path", "required": True,
                     "schema": {"type": "string"}},
                    {"name": "full", "in": "query", "schema": {"type": "boolean"}},
                ],
            }
        },
        "/items": {"post": {
            "operationId": "create_item", "summary": "Create an item",
            "requestBody": {"required": True, "content": {
                "application/json": {"schema": {"type": "object", "properties": {
                    "name": {"type": "string"}}}}
            }},
        }},
    },
}


@pytest.fixture()
def openapi_environment(monkeypatch, tmp_path):
    url = "https://api.company.test/v1"
    monkeypatch.setattr(openapi_module.get_settings(), "openapi_allowed_base_urls", url)
    engine = create_engine(f"sqlite:///{tmp_path / 'openapi.db'}",
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    monkeypatch.setattr(agent_module, "SessionLocal", factory)
    monkeypatch.setattr(tool_module, "SessionLocal", factory)
    monkeypatch.setattr(openapi_module, "SessionLocal", factory)
    agent_service.seed_built_ins()
    tool_service.seed_builtin_tools()
    tool_service.seed_builtin_assignments()

    approvals = ApprovalStore(str(tmp_path / "approvals.db"))
    monkeypatch.setattr(openapi_module, "approval_store", approvals)
    import app.modules.tools.mcp_service as mcp_module
    import app.api.platform as platform_module
    monkeypatch.setattr(mcp_module, "approval_store", approvals)
    monkeypatch.setattr(platform_module, "approval_store", approvals)
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        assert request.url.host == "api.company.test"
        if request.method == "GET":
            return httpx.Response(200, json={"id": request.url.path.split("/")[-1],
                                              "full": request.url.params.get("full")})
        return httpx.Response(201, json={"ok": True})

    monkeypatch.setattr(openapi_module.OpenAPIService, "_client",
                        lambda self, timeout: httpx.Client(
                            transport=httpx.MockTransport(handler),
                            timeout=timeout, follow_redirects=False, trust_env=False))
    return TestClient(app), approvals, requests, url


def _agent_with_tool(tool_id):
    agent = agent_service.create(AgentCreate(name="OpenAPI agent"), actor="admin")
    agent_service.publish(agent.id, 1)
    agent_service.create_version(agent.id, AgentVersionPatch(), actor="admin")
    tool_service.replace_version_tools(agent.id, 2, [tool_id])
    agent_service.publish(agent.id, 2)
    return agent.id


def test_openapi_register_policy_and_parameter_bound_invocation(openapi_environment):
    client, approvals, requests, url = openapi_environment
    denied = client.post("/api/v1/openapi/services", json={
        "name": "unsafe", "base_url": "http://127.0.0.1:9000", "document": DOCUMENT})
    assert denied.status_code == 400
    assert not requests

    created = client.post("/api/v1/openapi/services", json={
        "name": "Inventory", "base_url": url, "document": DOCUMENT})
    assert created.status_code == 201, created.text
    assert created.json()["operation_count"] == 2
    assert "operations" not in created.json()
    tools = [t for t in client.get("/api/v1/tools").json() if t["provider"] == "openapi"]
    assert len(tools) == 2
    assert all(t["approval_required"] and t["risk"] == "high" and t["mode"] == "write"
               for t in tools)
    get_tool = next(t for t in tools if t["name"] == "get_item")
    agent_id = _agent_with_tool(get_tool["id"])
    args = {"path": {"item_id": "A17"}, "query": {"full": True}}
    endpoint = f"/api/v1/openapi/agents/{agent_id}/tools/{get_tool['id']}/invoke"
    assert client.post(endpoint, json={"arguments": args}).status_code == 403

    approval = client.post("/api/v1/platform/approvals", json={
        "agent": get_tool["namespace"], "tool": get_tool["name"],
        "target": f"tool:{get_tool['id']}", "agent_id": agent_id,
        "agent_version": 2, "arguments": args})
    assert approval.status_code == 200, approval.text
    approval_id = approval.json()["id"]
    assert client.post(f"/api/v1/platform/approvals/{approval_id}/decision",
                       json={"decision": "approved"}).status_code == 200

    for tampered in (
        {"path": {"item_id": "B99"}, "query": {"full": True}},
        {"path": {"item_id": "A17"}, "query": {"full": False}},
    ):
        attempt = client.post(endpoint, json={"approval_id": approval_id, "arguments": tampered})
        assert attempt.status_code == 403
    assert not requests

    invoked = client.post(endpoint, json={"approval_id": approval_id, "arguments": args})
    assert invoked.status_code == 200, invoked.text
    assert invoked.json()["result"] == {"status_code": 200, "data": {"id": "A17", "full": "true"}}
    assert requests[0].url.path == "/v1/items/A17"
    assert approvals.get(approval_id).status == "consumed"
    assert client.post(endpoint, json={"approval_id": approval_id, "arguments": args}).status_code == 403
    assert len(requests) == 1


def test_openapi_import_and_runtime_validation(openapi_environment):
    client, _, requests, url = openapi_environment
    for document in (
        {**DOCUMENT, "paths": {"/../secret": {"get": {"operationId": "unsafe"}}}},
        {**DOCUMENT, "paths": {"/items": {"get": {"operationId": "read",
            "parameters": [{"name": "test", "in": "query",
                            "schema": {"$ref": "#/components/schemas/Foo"}}]}}}},
    ):
        response = client.post("/api/v1/openapi/services", json={
            "name": "invalid", "base_url": url, "document": document})
        assert response.status_code == 400, response.text

    imported = client.post("/api/v1/openapi/services", json={
        "name": "Inventory", "base_url": url, "document": DOCUMENT})
    assert imported.status_code == 201
    tool = next(t for t in client.get("/api/v1/tools").json()
                if t["provider"] == "openapi" and t["name"] == "get_item")
    agent_id = _agent_with_tool(tool["id"])
    endpoint = f"/api/v1/openapi/agents/{agent_id}/tools/{tool['id']}/invoke"
    for unsafe in (
        {"path": {"item_id": ".."}},
        {"path": {"item_id": "A/../../internal"}},
        {"path": {"item_id": "A17"}, "headers": {"Authorization": "Bearer injected"}},
        {"path": {"item_id": "A17"}, "query": {"evil": "unexpected"}},
    ):
        response = client.post(endpoint, json={"arguments": unsafe})
        assert response.status_code in (403, 409)
    assert not requests


def test_openapi_post_body_and_redirect_rejection(openapi_environment, monkeypatch):
    client, approvals, requests, url = openapi_environment
    assert client.post("/api/v1/openapi/services", json={
        "name": "Inventory", "base_url": url, "document": DOCUMENT}).status_code == 201
    tool = next(t for t in client.get("/api/v1/tools").json()
                if t["provider"] == "openapi" and t["name"] == "create_item")
    agent_id = _agent_with_tool(tool["id"])
    arguments = {"body": {"name": "Laptop"}}
    endpoint = f"/api/v1/openapi/agents/{agent_id}/tools/{tool['id']}/invoke"

    def approved():
        record = client.post("/api/v1/platform/approvals", json={
            "agent": tool["namespace"], "tool": tool["name"],
            "target": "tool:" + tool["id"], "agent_id": agent_id,
            "agent_version": 2, "arguments": arguments})
        assert record.status_code == 200, record.text
        approval_id = record.json()["id"]
        assert client.post(f"/api/v1/platform/approvals/{approval_id}/decision",
                           json={"decision": "approved"}).status_code == 200
        return approval_id

    first = approved()
    response = client.post(endpoint, json={"approval_id": first, "arguments": arguments})
    assert response.status_code == 200, response.text
    assert response.json()["result"]["status_code"] == 201
    assert requests[-1].method == "POST"
    assert requests[-1].url.path == "/v1/items"
    assert requests[-1].content == b'{"name":"Laptop"}'

    def redirect(request):
        requests.append(request)
        return httpx.Response(302, headers={"Location": "http://127.0.0.1/admin"})

    monkeypatch.setattr(openapi_module.OpenAPIService, "_client",
                        lambda self, timeout: httpx.Client(
                            transport=httpx.MockTransport(redirect),
                            timeout=timeout, follow_redirects=False, trust_env=False))
    second = approved()
    bad = client.post(endpoint, json={"approval_id": second, "arguments": arguments})
    assert bad.status_code == 502
    assert approvals.get(second).status == "consumed"
    assert len(requests) == 2  # 302 not followed


def test_openapi_generic_agent_propose_and_resume(openapi_environment, monkeypatch):
    client, approvals, requests, url = openapi_environment
    assert client.post("/api/v1/openapi/services", json={
        "name": "Inventory", "base_url": url, "document": DOCUMENT}).status_code == 201
    tool = next(t for t in client.get("/api/v1/tools").json()
                if t["provider"] == "openapi" and t["name"] == "get_item")
    agent_id = _agent_with_tool(tool["id"])

    class Model:
        def __init__(self, settings): pass
        def chat_with_tools(self, messages, definitions, **kwargs):
            assert len(definitions) == 1
            assert definitions[0]["function"]["name"].startswith("openapi_")
            return {"tool_calls": [{
                "id": "candidate", "type": "function",
                "function": {"name": definitions[0]["function"]["name"],
                             "arguments": '{"path":{"item_id":"A17"}}'},
            }]}
        def chat(self, messages, **kwargs): return "Inventory result A17"

    monkeypatch.setattr(runtime_module, "OpenAICompatibleLLM", Model)
    proposal = client.post(f"/api/v1/agents/{agent_id}/run", json={"input": "Find A17"})
    assert proposal.status_code == 200, proposal.text
    pending = proposal.json()["pending_tools"][0]
    assert pending["arguments"] == {"path": {"item_id": "A17"}}
    assert not requests

    submitted = client.post("/api/v1/platform/approvals", json={
        "agent": pending["namespace"], "tool": pending["tool"],
        "target": "tool:" + pending["tool_id"], "agent_id": agent_id,
        "agent_version": 2, "arguments": pending["arguments"]})
    assert submitted.status_code == 200, submitted.text
    approval_id = submitted.json()["id"]
    assert client.post(f"/api/v1/platform/approvals/{approval_id}/decision",
                       json={"decision": "approved"}).status_code == 200
    resume = client.post(f"/api/v1/agents/{agent_id}/approvals/{approval_id}/resume",
                         json={"input": "Find A17"})
    assert resume.status_code == 200, resume.text
    assert resume.json()["answer"] == "Inventory result A17"
    assert resume.json()["raw"]["result"]["data"]["id"] == "A17"
    assert approvals.get(approval_id).status == "consumed"
    assert len(requests) == 1
