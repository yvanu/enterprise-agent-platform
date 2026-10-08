"""MCP server discovery and governed invocation.

Every discovered tool is imported as high-risk/write/approval-required by
default. MCP tool annotations are untrusted and never grant capabilities.
"""
from __future__ import annotations

from datetime import datetime
from urllib.parse import urlsplit
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.config import get_settings
from app.modules.agents.db import SessionLocal
from app.modules.agents.orm import AgentORM
from app.modules.tools.mcp import MCPClient
from app.modules.tools.orm import MCPServerORM, ToolORM
from app.platform.approvals import approval_store
from app.platform.models import TraceStep
from app.platform.policy import require_tool, tool_execution_context
from app.platform.runs import start_run


class MCPServerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    url: str = Field(min_length=1, max_length=2048)


class MCPServerView(MCPServerCreate):
    id: str
    status: str
    created_at: datetime
    updated_at: datetime


class MCPInvocation(BaseModel):
    arguments: dict = Field(default_factory=dict)
    approval_id: int | None = Field(default=None, ge=1)


class MCPService:
    @staticmethod
    def _check_url(url: str) -> None:
        # Exact, operator-managed URL allowlist. No arbitrary user-provided SSRF.
        allowed = {item.strip() for item in get_settings().mcp_allowed_urls.split(",") if item.strip()}
        parts = urlsplit(url)
        if (url not in allowed or parts.scheme not in ("https", "http")
                or not parts.hostname or parts.username or parts.password
                or parts.query or parts.fragment
                or (get_settings().app_env.lower() in ("prod", "production")
                    and parts.scheme != "https")):
            raise ValueError("MCP URL must be an approved endpoint (MCP_ALLOWED_URLS); production requires HTTPS")

    def register(self, request: MCPServerCreate) -> MCPServerView:
        self._check_url(request.url)
        with SessionLocal() as session:
            item = MCPServerORM(id=str(uuid4()), name=request.name, url=request.url,
                                status="registered")
            session.add(item)
            session.commit()
            session.refresh(item)
            return MCPServerView.model_validate(item, from_attributes=True)

    def list(self) -> list[MCPServerView]:
        with SessionLocal() as session:
            return [MCPServerView.model_validate(item, from_attributes=True)
                    for item in session.scalars(select(MCPServerORM).order_by(MCPServerORM.created_at))]

    def discover(self, server_id: str) -> list:
        from app.modules.tools.service import tool_view

        with SessionLocal() as session:
            server = session.get(MCPServerORM, server_id)
            if server is None:
                raise KeyError("MCP Server 不存在")
            self._check_url(server.url)
            # Discover *before* mutating state; network failure leaves old tools alone.
            remote_tools = MCPClient(server.url).discover()
            namespace = f"mcp.{server.id}"
            seen = set()
            normalized = []
            for remote in remote_tools:
                if not isinstance(remote, dict):
                    raise ValueError("Invalid MCP tool descriptor")
                name = remote.get("name")
                if (not isinstance(name, str) or not name or len(name) > 100
                        or name in seen or len(f"{namespace}.{name}") > 160):
                    raise ValueError("Invalid or duplicate MCP tool name")
                seen.add(name)
                schema = remote.get("inputSchema", {"type": "object"})
                if not isinstance(schema, dict) or schema.get("type") != "object":
                    raise ValueError("MCP input schema must be an object")
                normalized.append((name, str(remote.get("description") or "")[:2000], schema))

            existing = {item.name: item for item in
                        session.scalars(select(ToolORM).where(ToolORM.namespace == namespace))}
            for name, description, schema in normalized:
                tool = existing.pop(name, None)
                if tool is None:
                    tool = ToolORM(id=str(uuid4()), key=f"{namespace}.{name}",
                                   namespace=namespace, name=name, mode="write",
                                   risk="high", approval_required=True,
                                   provider="mcp", type="mcp")
                    session.add(tool)
                tool.display_name = name
                tool.description = description
                tool.input_schema = schema
                tool.output_schema = {}
                tool.timeout_seconds = 15
                tool.enabled = True
                # Preserve existing policy: rediscovery may not reduce risk.
            for removed in existing.values():
                removed.enabled = False
            server.status = "connected"
            session.commit()
            return [tool_view(item) for item in session.scalars(
                select(ToolORM).where(ToolORM.namespace == namespace, ToolORM.enabled.is_(True))
            )]

    def call_assigned(self, agent_id: str, agent_version: int, tool_id: str,
                      request: MCPInvocation, *, actor: str) -> dict:
        """Invoke inside an Agent's published tool boundary; caller owns Run/Trace."""
        with SessionLocal() as session:
            agent = session.get(AgentORM, agent_id)
            if agent is None:
                raise KeyError("Agent 不存在")
            if agent.status != "published" or agent.published_version != agent_version:
                raise ValueError("Agent Version 不再是发布版本")
            tool = session.get(ToolORM, tool_id)
            if tool is None or tool.provider != "mcp" or not tool.enabled:
                raise KeyError("MCP Tool 不存在或已禁用")
            server = session.get(MCPServerORM, tool.namespace.removeprefix("mcp."))
            if server is None or server.status != "connected":
                raise ValueError("MCP Server 未连接")
            self._check_url(server.url)
            namespace, tool_name, mode = tool.namespace, tool.name, tool.mode
            url, timeout = server.url, tool.timeout_seconds

        with tool_execution_context(agent_id, agent_version):
            require_tool(namespace, tool_name, mode, approval_granted=bool(request.approval_id))
            if request.approval_id is not None:
                approval_store.consume(
                    request.approval_id, agent=namespace, tool=tool_name,
                    target=f"tool:{tool_id}", actor=actor,
                    arguments=request.arguments, agent_id=agent_id,
                    agent_version=agent_version,
                )
            result = MCPClient(url, timeout).call(tool_name, request.arguments)
            if result.get("isError"):
                raise RuntimeError("MCP tool returned isError")
            return result

    def invoke(self, agent_id: str, tool_id: str, request: MCPInvocation, *, actor: str) -> dict:
        with SessionLocal() as session:
            agent = session.get(AgentORM, agent_id)
            if agent is None:
                raise KeyError("Agent 不存在")
            if agent.status != "published" or agent.published_version is None:
                raise ValueError("Agent 尚未发布")
            agent_version, slug = agent.published_version, agent.slug
            tool = session.get(ToolORM, tool_id)
            tool_key = tool.key if tool else tool_id

        run = start_run(slug, agent_id=agent_id, agent_version=agent_version)
        try:
            result = self.call_assigned(agent_id, agent_version, tool_id, request, actor=actor)
            run_id = run.success([TraceStep(kind="tool", name=tool_key, detail="MCP invocation")])
            return {"run_id": run_id, "result": result}
        except Exception as exc:
            run.error(exc)
            raise


mcp_service = MCPService()
