from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


AgentType = Literal["generic", "data", "knowledge", "ops", "supervisor"]
AgentStatus = Literal["draft", "published", "archived"]
VersionStatus = Literal["draft", "published", "archived"]


class AgentVersionCreate(BaseModel):
    instructions: str = ""
    model_provider: str = "openai-compatible"
    model: str = ""
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1, le=1_000_000)
    max_steps: int = Field(default=8, ge=1, le=100)
    timeout_seconds: int = Field(default=60, ge=1, le=3600)
    tool_config: dict = Field(default_factory=dict)
    knowledge_config: dict = Field(default_factory=dict)
    data_config: dict = Field(default_factory=dict)
    guardrail_config: dict = Field(default_factory=dict)


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str | None = Field(default=None, max_length=120)
    description: str = Field(default="", max_length=2000)
    type: AgentType = "generic"
    version: AgentVersionCreate = Field(default_factory=AgentVersionCreate)


class AgentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)


class AgentVersionPatch(BaseModel):
    instructions: str | None = None
    model_provider: str | None = None
    model: str | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_tokens: int | None = Field(default=None, ge=1, le=1_000_000)
    max_steps: int | None = Field(default=None, ge=1, le=100)
    timeout_seconds: int | None = Field(default=None, ge=1, le=3600)
    tool_config: dict | None = None
    knowledge_config: dict | None = None
    data_config: dict | None = None
    guardrail_config: dict | None = None


class AgentVersionView(BaseModel):
    id: str
    agent_id: str
    version: int
    status: VersionStatus
    instructions: str
    model_provider: str
    model: str
    temperature: float
    max_tokens: int | None
    max_steps: int
    timeout_seconds: int
    tool_config: dict
    knowledge_config: dict
    data_config: dict
    guardrail_config: dict
    created_by: str
    created_at: datetime
    published_at: datetime | None = None


class AgentView(BaseModel):
    id: str
    name: str
    slug: str
    description: str
    type: AgentType
    status: AgentStatus
    built_in: bool
    published_version: int | None
    latest_version: int | None
    created_by: str
    created_at: datetime
    updated_at: datetime


class AgentDetail(AgentView):
    versions: list[AgentVersionView]


class AgentPublishRequest(BaseModel):
    version: int = Field(ge=1)


class AgentRunRequest(BaseModel):
    input: str = Field(min_length=1, max_length=20_000)
    source: str = "default"


class AgentRunResponse(BaseModel):
    run_id: int | None = None
    agent_id: str
    agent_version: int
    answer: str
    trace: list[dict] = Field(default_factory=list)
    raw: dict | None = None
