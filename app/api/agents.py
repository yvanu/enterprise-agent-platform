from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.modules.agents.models import (
    AgentCreate,
    AgentDetail,
    AgentPublishRequest,
    AgentRunRequest,
    AgentRunResponse,
    AgentUpdate,
    AgentVersionPatch,
    AgentVersionView,
    AgentView,
)
from app.modules.agents.runtime import agent_runtime
from app.modules.agents.service import agent_service
from app.platform.auth import Identity, current_identity, require_roles
from app.platform.llm import LLMNotConfiguredError


router = APIRouter(prefix="/api/v1/agents", tags=["agents"])


@router.get("", response_model=list[AgentView])
def list_agents() -> list[AgentView]:
    return agent_service.list()


@router.post("", response_model=AgentDetail, status_code=status.HTTP_201_CREATED)
def create_agent(
    request: AgentCreate,
    identity: Annotated[Identity, Depends(require_roles("operator", "admin"))],
) -> AgentDetail:
    return agent_service.create(request, actor=identity.username)


@router.get("/{agent_id}", response_model=AgentDetail)
def get_agent(agent_id: str) -> AgentDetail:
    result = agent_service.get(agent_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Agent 不存在")
    return result


@router.patch("/{agent_id}", response_model=AgentDetail)
def update_agent(
    agent_id: str,
    request: AgentUpdate,
    identity: Annotated[Identity, Depends(require_roles("operator", "admin"))],
) -> AgentDetail:
    try:
        return agent_service.update(agent_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{agent_id}/versions", response_model=list[AgentVersionView])
def list_agent_versions(agent_id: str) -> list[AgentVersionView]:
    result = agent_service.get(agent_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Agent 不存在")
    return result.versions


@router.post("/{agent_id}/versions", response_model=AgentVersionView, status_code=status.HTTP_201_CREATED)
def create_agent_version(
    agent_id: str,
    request: AgentVersionPatch,
    identity: Annotated[Identity, Depends(require_roles("operator", "admin"))],
) -> AgentVersionView:
    try:
        return agent_service.create_version(agent_id, request, actor=identity.username)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{agent_id}/publish", response_model=AgentDetail)
def publish_agent(
    agent_id: str,
    request: AgentPublishRequest,
    identity: Annotated[Identity, Depends(require_roles("operator", "admin"))],
) -> AgentDetail:
    version = request.version
    try:
        return agent_service.publish(agent_id, version)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{agent_id}/publish/{version}", response_model=AgentDetail, include_in_schema=False)
def publish_agent_compat(
    agent_id: str,
    version: int,
    identity: Annotated[Identity, Depends(require_roles("operator", "admin"))],
) -> AgentDetail:
    return publish_agent(agent_id, AgentPublishRequest(version=version), identity)


@router.post("/{agent_id}/archive", response_model=AgentDetail)
def archive_agent(
    agent_id: str,
    identity: Annotated[Identity, Depends(require_roles("admin"))],
) -> AgentDetail:
    try:
        return agent_service.archive(agent_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/{agent_id}/run", response_model=AgentRunResponse)
def run_agent(
    agent_id: str,
    request: AgentRunRequest,
    identity: Annotated[Identity, Depends(current_identity)],
) -> AgentRunResponse:
    agent = agent_service.get(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent 不存在")
    try:
        return agent_runtime.run(agent, request, identity)
    except LLMNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
