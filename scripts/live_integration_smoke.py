#!/usr/bin/env python3
"""Opt-in live HTTPS smoke for two public, read-only external services.

Isolated API TestClient + temporary databases, real MCP/REST HTTPS transport.
No external LLM call, no production service, no real credentials or writes.
Run: nice -n 15 timeout 65s .venv/bin/python scripts/live_integration_smoke.py --run-live
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path


MCP_URL = "https://mcp.deepwiki.com/mcp"
REST_URL = "https://jsonplaceholder.typicode.com"


def run_smoke() -> int:
    with tempfile.TemporaryDirectory(prefix="eap-external-smoke-") as directory:
        # Set these BEFORE importing app.main: its initialization seeds stores.
        root = Path(directory)
        os.environ.update({
            "APP_ENV": "development",
            "AUTH_ENABLED": "false",
            "DATABASE_URL": f"sqlite:///{root / 'demo.db'}",
            "PLATFORM_DATABASE_URL": f"sqlite:///{root / 'resources.db'}",
            "PLATFORM_DB_PATH": str(root / "runs.db"),
            "KNOWLEDGE_DB_PATH": str(root / "knowledge.db"),
            "MCP_ALLOWED_URLS": MCP_URL,
            "OPENAPI_ALLOWED_BASE_URLS": REST_URL,
        })

        from fastapi.testclient import TestClient
        from app.main import app
        from app.modules.agents import runtime as runtime_module
        from app.modules.agents.models import AgentCreate, AgentVersionPatch
        from app.modules.agents.service import agent_service
        from app.modules.tools.service import tool_service
        from app.platform.approvals import approval_store
        from app.platform.runs import run_store

        class PredictableLLM:
            arguments = {}

            def __init__(self, settings):
                pass

            def chat_with_tools(self, messages, definitions, **kwargs):
                assert len(definitions) == 1
                return {"tool_calls": [{
                    "id": "live-readonly-call",
                    "type": "function",
                    "function": {
                        "name": definitions[0]["function"]["name"],
                        "arguments": json.dumps(self.arguments),
                    },
                }]}

            def chat(self, messages, **kwargs):
                return "External read-only tool invocation completed"

        # Every LLM turn uses deterministic JSON. The external tool call is REAL.
        runtime_module.OpenAICompatibleLLM = PredictableLLM

        def http_ok(response, label):
            if not response.is_success:
                raise AssertionError(f"{label}: HTTP {response.status_code}: {response.text[:450]}")
            return response.json()

        def publish(tool, title):
            agent = agent_service.create(AgentCreate(name=title), actor="smoke")
            agent_service.publish(agent.id, 1)
            agent_service.create_version(agent.id, AgentVersionPatch(), actor="smoke")
            tool_service.replace_version_tools(agent.id, 2, [tool["id"]])
            agent_service.publish(agent.id, 2)
            return agent.id

        def approve_and_resume(client, agent_id, tool, arguments):
            PredictableLLM.arguments = arguments
            request = {"input": "Read this public test resource"}
            proposed = http_ok(client.post(f"/api/v1/agents/{agent_id}/run", json=request),
                               "Agent proposal")
            assert proposed["pending_tools"] == [{
                "tool_id": tool["id"], "namespace": tool["namespace"],
                "tool": tool["name"], "arguments": arguments,
            }]
            assert run_store.get(proposed["run_id"]).status == "waiting_approval"
            created = http_ok(client.post("/api/v1/platform/approvals", json={
                "agent": tool["namespace"], "tool": tool["name"],
                "target": f"tool:{tool['id']}",
                "agent_id": agent_id, "agent_version": 2,
                "arguments": arguments,
            }), "Create approval")
            approval_id = created["id"]
            resume_url = f"/api/v1/agents/{agent_id}/approvals/{approval_id}/resume"
            assert client.post(resume_url, json=request).status_code == 403
            http_ok(client.post(
                f"/api/v1/platform/approvals/{approval_id}/decision",
                json={"decision": "approved"},
            ), "Approve")
            finished = http_ok(client.post(resume_url, json=request), "Resume")
            assert run_store.get(finished["run_id"]).status == "ok"
            assert approval_store.get(approval_id).status == "consumed"
            assert client.post(resume_url, json=request).status_code == 403
            return finished

        with TestClient(app) as client:
            # Actual MCP Streamable HTTP initialize, tools/list, then tools/call.
            registered = http_ok(client.post("/api/v1/mcp/servers", json={
                "name": "DeepWiki public read-only",
                "url": MCP_URL,
            }), "Register MCP")
            discovered = http_ok(client.post(
                f"/api/v1/mcp/servers/{registered['id']}/discover",
            ), "MCP discover")
            tool = next(row for row in discovered if row["name"] == "read_wiki_structure")
            assert tool["provider"] == "mcp" and tool["approval_required"]
            mcp_agent = publish(tool, "Live DeepWiki read-only agent")
            finished = approve_and_resume(
                client, mcp_agent, tool, {"repoName": "pallets/flask"})
            data = finished["raw"]["result"]
            assert data.get("isError") is not True
            assert "Available pages for pallets/flask" in str(data.get("content", []))
            print("PASS live MCP: HTTPS initialize + discovery + approved read_wiki_structure + replay reject")
            print("  discovered_count=", len(discovered), "tool=", tool["name"],
                  "result_chars=", len(str(data.get("content", []))))

            # Real HTTPS GET (no POST side effects), fixed API base allowlist.
            doc = {
                "openapi": "3.0.3",
                "info": {"title": "Public JSONPlaceholder", "version": "1"},
                "paths": {"/todos/{id}": {"get": {
                    "operationId": "get_todo",
                    "parameters": [{
                        "in": "path", "name": "id", "required": True,
                        "schema": {"type": "integer"},
                    }],
                }}},
            }
            api = http_ok(client.post("/api/v1/openapi/services", json={
                "name": "JSONPlaceholder public read-only",
                "base_url": REST_URL, "document": doc,
            }), "Register REST")
            rest_tool = next(x for x in client.get("/api/v1/tools").json()
                             if x["namespace"] == f"openapi.{api['id']}")
            assert rest_tool["approval_required"] and rest_tool["provider"] == "openapi"
            rest_agent = publish(rest_tool, "Live JSONPlaceholder read-only agent")
            finished = approve_and_resume(
                client, rest_agent, rest_tool, {"path": {"id": 1}})
            assert finished["raw"]["result"]["status_code"] == 200
            payload = finished["raw"]["result"]["data"]
            assert payload["id"] == 1 and "title" in payload
            print("PASS live REST: HTTPS GET /todos/1 + approved Agent resume + replay reject")
            print("  todo_id=", payload["id"], "title_length=", len(payload["title"]))

        print("PASS both live external read-only endpoints; all test data discarded")
        return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-live", action="store_true",
                        help="Confirm intentional outbound HTTPS requests to public read-only endpoints")
    if not parser.parse_args().run_live:
        parser.error("External network testing is opt-in: pass --run-live")
    try:
        sys.exit(run_smoke())
    except Exception as exc:
        print("FAIL external smoke:", type(exc).__name__, str(exc)[:500], file=sys.stderr)
        raise
