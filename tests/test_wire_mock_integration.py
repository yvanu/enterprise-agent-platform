"""Loopback-wire integration: real HTTPX sockets, isolated fake MCP/REST server.

No production URLs, credentials, database changes, LLM calls, or long-running
processes. The HTTP server binds only to 127.0.0.1 on an ephemeral port.
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.config import get_settings
from app.modules.agents import runtime as runtime_module
from app.modules.agents import service as agent_module
from app.modules.agents.models import AgentCreate, AgentVersionPatch
from app.modules.agents.service import agent_service
from app.modules.agents.base import Base
from app.modules.tools import mcp_service as mcp_module
from app.modules.tools import openapi_service as openapi_module
from app.modules.tools import service as tools_module
from app.modules.tools.service import tool_service
from app.platform import runs as runs_module
from app.platform.approvals import ApprovalStore
from app.platform.runs import RunStore


class LocalMockHandler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def _respond(self, status, payload=None, *, content_type="application/json", extra=None):
        body = (json.dumps(payload).encode("utf-8")
                if content_type == "application/json" else (payload or b""))
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        path = urlsplit(self.path).path
        size = int(self.headers.get("Content-Length", 0))
        assert size < 65536, "mock request too large"
        data = json.loads(self.rfile.read(size) or "{}")
        if path == "/mcp":
            method = data["method"]
            self.server.events.append(("mcp", method, data.get("params", {}),
                                       self.headers.get("Mcp-Session-Id")))
            if method == "initialize":
                self._respond(200, {"jsonrpc": "2.0", "id": data["id"],
                                    "result": {"protocolVersion": "2025-03-26", "capabilities": {"tools": {}}}},
                              extra={"Mcp-Session-Id": "loopback-session"})
                return
            if method == "notifications/initialized":
                self._respond(202)
                return
            if method == "tools/list":
                response = {"jsonrpc": "2.0", "id": data["id"],
                            "result": {"tools": [
                                {"name": "lookup", "description": "Local read-only mock",
                                 "inputSchema": {"type": "object",
                                                 "properties": {"q": {"type": "string"}},
                                                 "required": ["q"]}}
                            ]}}
                wire = ("event: message\\ndata: " + json.dumps(response) + "\\n\\n").replace(
                    "\\n", "\n").encode()
                self._respond(200, wire, content_type="text/event-stream")
                return
            if method == "tools/call":
                assert self.headers.get("Mcp-Session-Id") == "loopback-session"
                params = data["params"]
                response = {"jsonrpc": "2.0", "id": data["id"],
                            "result": {"content": [
                                {"type": "text", "text": "mock_mcp:" + params["arguments"]["q"]}
                            ]}}
                self._respond(200, response)
                return
            self._respond(404, {"error": "unrecognized MCP method"})
            return

        if path == "/v1/items":
            self.server.events.append(("rest_post", data))
            self._respond(201, {"received": data, "source": "real_loopback_socket"})
            return
        self._respond(404, {"error": "not found"})

    def do_GET(self):
        parsed = urlsplit(self.path)
        if parsed.path == "/v1/items/redirect":
            self.server.events.append(("rest_redirect",))
            self._respond(302, b"", content_type="text/plain",
                          extra={"Location": "http://127.0.0.1:1/private"})
            return
        if parsed.path.startswith("/v1/items/"):
            item = parsed.path.removeprefix("/v1/items/")
            self.server.events.append(("rest_get", item, parse_qs(parsed.query)))
            self._respond(200, {"item_id": item, "from": "real_loopback_socket",
                                "full": parse_qs(parsed.query).get("full", [None])[0]})
            return
        self._respond(404, {"error": "not found"})


@pytest.fixture()
def wire_env(tmp_path, monkeypatch):
    server = ThreadingHTTPServer(("127.0.0.1", 0), LocalMockHandler)
    server.daemon_threads = True
    server.events = []
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    address = f"http://127.0.0.1:{server.server_port}"
    settings = get_settings()
    monkeypatch.setattr(settings, "app_env", "development")
    monkeypatch.setattr(settings, "mcp_allowed_urls", address + "/mcp")
    monkeypatch.setattr(settings, "openapi_allowed_base_urls", address + "/v1")

    # Keep all platform, approval and Run records outside the production data/ dir.
    engine = create_engine(f"sqlite:///{tmp_path / 'platform.db'}",
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False, future=True)
    for module in (agent_module, tools_module, mcp_module, openapi_module):
        monkeypatch.setattr(module, "SessionLocal", factory)
    agent_service.seed_built_ins()
    tool_service.seed_builtin_tools()
    tool_service.seed_builtin_assignments()

    approvals = ApprovalStore(str(tmp_path / "approvals.db"))
    for module in (mcp_module, openapi_module):
        monkeypatch.setattr(module, "approval_store", approvals)
    import app.api.platform as platform_api
    monkeypatch.setattr(platform_api, "approval_store", approvals)
    monkeypatch.setattr(runs_module, "run_store", RunStore(str(tmp_path / "runs.db")))
    monkeypatch.setattr(settings, "auth_enabled", False)

    try:
        with TestClient(app) as client:
            yield client, server, approvals, address
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=3)
        engine.dispose()


def _published_agent(tool_id, name):
    agent = agent_service.create(AgentCreate(name=name), actor="admin")
    agent_service.publish(agent.id, 1)
    agent_service.create_version(agent.id, AgentVersionPatch(), actor="admin")
    tool_service.replace_version_tools(agent.id, 2, [tool_id])
    agent_service.publish(agent.id, 2)
    return agent.id


def _propose_approve_resume(client, monkeypatch, agent_id, tool, arguments, approvals):
    class MockLLM:
        def __init__(self, settings): pass

        def chat_with_tools(self, messages, definitions, **kwargs):
            assert len(definitions) == 1
            return {"tool_calls": [{"type": "function", "id": "mock-call",
                                    "function": {"name": definitions[0]["function"]["name"],
                                                 "arguments": json.dumps(arguments)}}]}

        def chat(self, messages, **kwargs):
            return "LLM mock summary (no external AI call)"

    monkeypatch.setattr(runtime_module, "OpenAICompatibleLLM", MockLLM)
    proposed = client.post(f"/api/v1/agents/{agent_id}/run",
                           json={"input": "Lookup an item"})
    assert proposed.status_code == 200, proposed.text
    p = proposed.json()
    assert runs_module.run_store.get(p["run_id"]).status == "waiting_approval"
    assert p["pending_tools"] == [{"tool_id": tool["id"], "tool": tool["name"],
                                   "namespace": tool["namespace"], "arguments": arguments}]

    created = client.post("/api/v1/platform/approvals", json={
        "agent": tool["namespace"], "tool": tool["name"],
        "target": f"tool:{tool['id']}", "arguments": arguments,
        "agent_id": agent_id, "agent_version": 2})
    assert created.status_code == 200, created.text
    approval_id = created.json()["id"]
    resume_path = f"/api/v1/agents/{agent_id}/approvals/{approval_id}/resume"
    assert client.post(resume_path, json={"input": "Lookup an item"}).status_code == 403
    assert client.post(f"/api/v1/platform/approvals/{approval_id}/decision",
                       json={"decision": "approved"}).status_code == 200
    completed = client.post(resume_path, json={"input": "Lookup an item"})
    assert completed.status_code == 200, completed.text
    assert completed.json()["answer"] == "LLM mock summary (no external AI call)"
    assert runs_module.run_store.get(completed.json()["run_id"]).status == "ok"
    assert approvals.get(approval_id).status == "consumed"
    assert client.post(resume_path, json={"input": "Lookup an item"}).status_code == 403
    return completed.json()


def test_real_socket_mcp_discovery_sse_approval_resume(wire_env, monkeypatch):
    client, server, approvals, url = wire_env
    created = client.post("/api/v1/mcp/servers", json={
        "name": "Local TCP MCP", "url": url + "/mcp"})
    assert created.status_code == 201, created.text
    discovered = client.post(f"/api/v1/mcp/servers/{created.json()['id']}/discover")
    assert discovered.status_code == 200, discovered.text
    tool = discovered.json()[0]
    assert tool["risk"] == "high" and tool["approval_required"]
    assert [event[1] for event in server.events if event[0] == "mcp"] == [
        "initialize", "notifications/initialized", "tools/list",
    ]
    assert not any(e[1] == "tools/call" for e in server.events if e[0] == "mcp")

    agent_id = _published_agent(tool["id"], "TCP MCP Agent")
    arguments = {"q": "river_level"}
    result = _propose_approve_resume(client, monkeypatch, agent_id, tool, arguments, approvals)
    assert result["raw"]["result"]["content"][0]["text"] == "mock_mcp:river_level"
    assert [event[1] for event in server.events if event[0] == "mcp"].count("tools/call") == 1
    assert next(e for e in server.events if e[0] == "mcp" and e[1] == "tools/call")[3] == "loopback-session"
    assert len(result["trace"]) == 1


def test_real_socket_rest_get_post_approval_replay(wire_env, monkeypatch):
    client, server, approvals, url = wire_env
    doc = {"openapi": "3.0.3", "info": {"title": "Local Inventory", "version": "1"},
           "paths": {
               "/items/{item_id}": {"get": {"operationId": "lookup_item", "parameters": [
                   {"name": "item_id", "in": "path", "required": True,
                    "schema": {"type": "string"}},
                   {"name": "full", "in": "query", "schema": {"type": "boolean"}},
               ]}},
               "/items": {"post": {"operationId": "create_item",
                                   "requestBody": {"required": True, "content": {
                                       "application/json": {"schema": {"type": "object", "properties": {
                                           "name": {"type": "string"}}}}
                                   }}}},
           }}
    created = client.post("/api/v1/openapi/services", json={
        "name": "Local TCP REST", "base_url": url + "/v1", "document": doc})
    assert created.status_code == 201, created.text
    assert created.json()["operation_count"] == 2
    tools = {t["name"]: t for t in client.get("/api/v1/tools").json()
             if t["namespace"] == "openapi." + created.json()["id"]}
    tool = tools["lookup_item"]
    agent_id = _published_agent(tool["id"], "TCP REST Agent")
    arguments = {"path": {"item_id": "A17"}, "query": {"full": True}}
    assert server.events == []
    result = _propose_approve_resume(client, monkeypatch, agent_id, tool, arguments, approvals)
    assert result["raw"]["result"]["data"] == {
        "item_id": "A17", "from": "real_loopback_socket", "full": "true"}
    assert server.events == [("rest_get", "A17", {"full": ["true"]})]

    # Verify true network POST separately, including exact body and one-shot approval.
    post_tool = tools["create_item"]
    post_agent = _published_agent(post_tool["id"], "TCP REST POST Agent")
    post_args = {"body": {"name": "sensor-1"}}
    post_result = _propose_approve_resume(
        client, monkeypatch, post_agent, post_tool, post_args, approvals)
    assert post_result["raw"]["result"]["status_code"] == 201
    assert server.events[-1] == ("rest_post", {"name": "sensor-1"})
    assert len(server.events) == 2


def test_real_socket_redirect_blocked_before_following(wire_env):
    client, server, approvals, url = wire_env
    doc = {"openapi": "3.0.3", "info": {"title": "No redirect", "version": "1"},
           "paths": {"/items/{item_id}": {"get": {
               "operationId": "lookup_item", "parameters": [
                   {"name": "item_id", "in": "path", "required": True,
                    "schema": {"type": "string"}}]}}}}
    registered = client.post("/api/v1/openapi/services", json={
        "name": "Redirect mock", "base_url": url + "/v1", "document": doc})
    assert registered.status_code == 201, registered.text
    tool = next(item for item in client.get("/api/v1/tools").json()
                if item["namespace"] == "openapi." + registered.json()["id"])
    agent_id = _published_agent(tool["id"], "Redirect safety agent")
    arguments = {"path": {"item_id": "redirect"}}
    approval = client.post("/api/v1/platform/approvals", json={
        "agent": tool["namespace"], "tool": tool["name"],
        "target": f"tool:{tool['id']}", "agent_id": agent_id,
        "agent_version": 2, "arguments": arguments})
    assert approval.status_code == 200, approval.text
    approval_id = approval.json()["id"]
    assert client.post(f"/api/v1/platform/approvals/{approval_id}/decision",
                       json={"decision": "approved"}).status_code == 200

    endpoint = f"/api/v1/openapi/agents/{agent_id}/tools/{tool['id']}/invoke"
    response = client.post(endpoint, json={"approval_id": approval_id,
                                           "arguments": arguments})
    assert response.status_code == 502
    assert server.events == [("rest_redirect",)]
    assert approvals.get(approval_id).status == "consumed"
    assert client.post(endpoint, json={"approval_id": approval_id,
                                       "arguments": arguments}).status_code == 403
    assert server.events == [("rest_redirect",)]
