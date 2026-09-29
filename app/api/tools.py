from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.modules.tools.models import AgentToolView, ToolAssignmentUpdate, ToolView
from app.modules.tools.service import tool_service
from app.platform.auth import Identity, require_roles


router = APIRouter(tags=["tools"])


@router.get("/api/v1/tools", response_model=list[ToolView])
def list_tools(
    namespace: str | None = Query(default=None),
    enabled_only: bool = Query(default=False),
) -> list[ToolView]:
    return tool_service.list(namespace=namespace, enabled_only=enabled_only)


@router.get("/api/v1/tools/{tool_id}", response_model=ToolView)
def get_tool(tool_id: str) -> ToolView:
    item = tool_service.get(tool_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Tool 不存在")
    return item


@router.get(
    "/api/v1/agents/{agent_id}/versions/{version}/tools",
    response_model=list[AgentToolView],
)
def list_agent_version_tools(agent_id: str, version: int) -> list[AgentToolView]:
    try:
        return tool_service.list_version_tools(agent_id, version)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.put(
    "/api/v1/agents/{agent_id}/versions/{version}/tools",
    response_model=list[AgentToolView],
)
def replace_agent_version_tools(
    agent_id: str,
    version: int,
    request: ToolAssignmentUpdate,
    identity: Annotated[Identity, Depends(require_roles("operator", "admin"))],
) -> list[AgentToolView]:
    try:
        return tool_service.replace_version_tools(agent_id, version, request.tool_ids)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
