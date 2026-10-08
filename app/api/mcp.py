from __future__ import annotations

import httpx
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.tools.mcp import MCPError
from app.modules.tools.mcp_service import MCPInvocation, MCPServerCreate, MCPServerView, mcp_service
from app.modules.tools.models import ToolView
from app.platform.auth import Identity, require_roles

router = APIRouter(prefix="/api/v1", tags=["mcp"])


@router.get("/mcp/servers", response_model=list[MCPServerView])
def list_mcp_servers() -> list[MCPServerView]:
    return mcp_service.list()


@router.post("/mcp/servers", response_model=MCPServerView, status_code=status.HTTP_201_CREATED)
def create_mcp_server(request: MCPServerCreate,
                      identity: Annotated[Identity, Depends(require_roles("admin"))]) -> MCPServerView:
    try:
        return mcp_service.register(request)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@router.post("/mcp/servers/{server_id}/discover", response_model=list[ToolView])
def discover_mcp_tools(server_id: str,
                       identity: Annotated[Identity, Depends(require_roles("admin"))]) -> list[ToolView]:
    try:
        return mcp_service.discover(server_id)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except (ValueError, MCPError, httpx.HTTPError) as exc:
        raise HTTPException(400, f"MCP discovery failed: {exc}") from exc


@router.post("/agents/{agent_id}/tools/{tool_id}/invoke")
def invoke_mcp_tool(agent_id: str, tool_id: str, request: MCPInvocation,
                    identity: Annotated[Identity, Depends(require_roles("operator", "admin"))]) -> dict:
    try:
        return mcp_service.invoke(agent_id, tool_id, request, actor=identity.username)
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(403, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    except (MCPError, httpx.HTTPError) as exc:
        raise HTTPException(502, f"MCP execution failed: {exc}") from exc
