from __future__ import annotations

import httpx
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.tools.mcp_service import MCPInvocation
from app.modules.tools.openapi_service import (
    OpenAPIServiceCreate, OpenAPIServiceView, openapi_service,
)
from app.platform.auth import Identity, require_roles

router = APIRouter(prefix="/api/v1", tags=["openapi"])


@router.get("/openapi/services", response_model=list[OpenAPIServiceView])
def list_openapi_services() -> list[OpenAPIServiceView]:
    return openapi_service.list()


@router.post("/openapi/services", response_model=OpenAPIServiceView,
             status_code=status.HTTP_201_CREATED)
def register_openapi_service(
    request: OpenAPIServiceCreate,
    identity: Annotated[Identity, Depends(require_roles("admin"))],
) -> OpenAPIServiceView:
    try:
        return openapi_service.register(request)
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/openapi/agents/{agent_id}/tools/{tool_id}/invoke")
def invoke_openapi_tool(
    agent_id: str, tool_id: str, request: MCPInvocation,
    identity: Annotated[Identity, Depends(require_roles("operator", "admin"))],
) -> dict:
    try:
        return openapi_service.invoke(agent_id, tool_id, request, actor=identity.username)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"OpenAPI execution failed: {exc}") from exc
