"""Minimal MCP Streamable HTTP client (JSON and SSE responses).

Supports initialize, notifications/initialized, tools/list with pagination,
and tools/call. No stdio, OAuth, remote resources, or resumable sessions.
"""
from __future__ import annotations

import json

import httpx


class MCPError(RuntimeError):
    pass


class MCPClient:
    PROTOCOL_VERSION = "2025-03-26"
    MAX_BODY_BYTES = 1024 * 1024

    def __init__(self, url: str, timeout_seconds: int = 15):
        self.url = url
        self.timeout_seconds = timeout_seconds

    def _client(self) -> httpx.Client:
        # Do not accept ambient proxy settings for endpoints controlled by
        # the platform allowlist; never follow redirects to a different host.
        return httpx.Client(timeout=self.timeout_seconds, follow_redirects=False, trust_env=False)

    def _request(self, client: httpx.Client, method: str, params: dict | None,
                 request_id: int | None, session_id: str | None) -> tuple[dict, str | None]:
        payload = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        if request_id is not None:
            payload["id"] = request_id
        headers = {"Accept": "application/json, text/event-stream",
                   "Content-Type": "application/json",
                   "MCP-Protocol-Version": self.PROTOCOL_VERSION}
        if session_id:
            headers["Mcp-Session-Id"] = session_id
        with client.stream("POST", self.url, headers=headers, json=payload) as response:
            response.raise_for_status()
            if response.is_redirect:
                raise MCPError("MCP endpoint redirects are not allowed")
            session = response.headers.get("Mcp-Session-Id") or session_id
            if request_id is None:  # initialized notification: 202 / no body is valid
                return {}, session
            content = bytearray()
            for chunk in response.iter_bytes():
                content.extend(chunk)
                if len(content) > self.MAX_BODY_BYTES:
                    raise MCPError("MCP response too large")
            body = content.decode("utf-8")
            if "text/event-stream" in response.headers.get("Content-Type", ""):
                packets = []
                for block in body.replace("\r\n", "\n").split("\n\n"):
                    lines = [line[5:].strip() for line in block.splitlines() if line.startswith("data:")]
                    if lines:
                        packets.append("\n".join(lines))
                results = [json.loads(p) for p in packets if p and p != "[DONE]"]
                message = next((x for x in results if x.get("id") == request_id), None)
                if message is None:
                    raise MCPError("MCP SSE response did not contain the expected id")
            else:
                message = json.loads(body)
            if not isinstance(message, dict) or message.get("id") != request_id:
                raise MCPError("Invalid MCP JSON-RPC response")
            if message.get("error"):
                raise MCPError(f"MCP error: {message['error'].get('message', 'unknown')}")
            result = message.get("result")
            if not isinstance(result, dict):
                raise MCPError("Invalid MCP result")
            return result, session

    def _connected(self, action):
        with self._client() as client:
            result, session = self._request(
                client, "initialize",
                {"protocolVersion": self.PROTOCOL_VERSION,
                 "capabilities": {},
                 "clientInfo": {"name": "enterprise-agent-platform", "version": "0.2"}},
                1, None,
            )
            if not result.get("protocolVersion"):
                raise MCPError("MCP server did not initialize")
            self._request(client, "notifications/initialized", None, None, session)
            return action(client, session)

    def discover(self) -> list[dict]:
        def fetch(client, session):
            tools = []
            cursor = None
            for page in range(20):
                result, _ = self._request(
                    client, "tools/list", {"cursor": cursor} if cursor else {}, page + 2, session,
                )
                batch = result.get("tools", [])
                if not isinstance(batch, list) or len(tools) + len(batch) > 100:
                    raise MCPError("MCP tool catalog too large")
                tools.extend(batch)
                cursor = result.get("nextCursor")
                if not cursor:
                    return tools
            raise MCPError("MCP pagination limit exceeded")
        return self._connected(fetch)

    def call(self, name: str, arguments: dict) -> dict:
        def invoke(client, session):
            result, _ = self._request(
                client, "tools/call", {"name": name, "arguments": arguments}, 2, session,
            )
            return result
        return self._connected(invoke)
