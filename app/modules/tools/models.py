from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


ToolMode = Literal["read", "write"]
ToolRisk = Literal["low", "medium", "high"]


class ToolView(BaseModel):
    id: str
    key: str
    name: str
    display_name: str
    description: str
    namespace: str
    provider: str
    type: str
    mode: ToolMode
    risk: ToolRisk
    approval_required: bool
    input_schema: dict
    output_schema: dict
    timeout_seconds: int
    enabled: bool
    created_at: datetime
    updated_at: datetime


class AgentToolView(BaseModel):
    id: str
    agent_version_id: str
    tool: ToolView
    enabled: bool
    config: dict
    created_at: datetime


class ToolAssignmentUpdate(BaseModel):
    tool_ids: list[str] = Field(default_factory=list)
