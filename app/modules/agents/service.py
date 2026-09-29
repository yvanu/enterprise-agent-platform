from __future__ import annotations

from dataclasses import dataclass

from app.modules.agents.db import SessionLocal, initialize_agent_store
from app.modules.agents.models import (
    AgentCreate,
    AgentDetail,
    AgentUpdate,
    AgentVersionCreate,
    AgentVersionPatch,
    AgentVersionView,
    AgentView,
)
from app.modules.agents.orm import AgentORM, AgentVersionORM
from app.modules.agents.repository import AgentRepository


BUILT_INS = [
    AgentCreate(
        name="Data Agent",
        slug="data-agent",
        description="Natural-language analytics with schema-aware, guarded SQL.",
        type="data",
        version=AgentVersionCreate(
            instructions="Use schema-aware, read-only SQL analysis and summarize only returned data.",
            tool_config={"preset": "data"},
        ),
    ),
    AgentCreate(
        name="Knowledge Agent",
        slug="knowledge-agent",
        description="Role-scoped retrieval with citations and versioned knowledge.",
        type="knowledge",
        version=AgentVersionCreate(
            instructions="Answer from role-scoped enterprise knowledge and preserve source citations.",
            tool_config={"preset": "knowledge"},
        ),
    ),
    AgentCreate(
        name="Ops Agent",
        slug="ops-agent",
        description="Infrastructure evidence, diagnostics, and governed actions.",
        type="ops",
        version=AgentVersionCreate(
            instructions="Diagnose from read-only operations evidence. Do not execute unapproved changes.",
            tool_config={"preset": "ops"},
        ),
    ),
    AgentCreate(
        name="Supervisor",
        slug="supervisor",
        description="Cross-agent incident investigation and evidence synthesis.",
        type="supervisor",
        version=AgentVersionCreate(
            instructions="Delegate to domain agents, preserve evidence boundaries, and synthesize conclusions.",
            tool_config={"preset": "supervisor"},
        ),
    ),
]


def version_view(item: AgentVersionORM) -> AgentVersionView:
    return AgentVersionView(
        id=item.id,
        agent_id=item.agent_id,
        version=item.version,
        status=item.status,
        instructions=item.instructions,
        model_provider=item.model_provider,
        model=item.model,
        temperature=item.temperature,
        max_tokens=item.max_tokens,
        max_steps=item.max_steps,
        timeout_seconds=item.timeout_seconds,
        tool_config=item.tool_config or {},
        knowledge_config=item.knowledge_config or {},
        data_config=item.data_config or {},
        guardrail_config=item.guardrail_config or {},
        created_by=item.created_by,
        created_at=item.created_at,
        published_at=item.published_at,
    )


def agent_view(item: AgentORM) -> AgentView:
    latest = max((version.version for version in item.versions), default=None)
    return AgentView(
        id=item.id,
        name=item.name,
        slug=item.slug,
        description=item.description,
        type=item.type,
        status=item.status,
        built_in=item.built_in,
        published_version=item.published_version,
        latest_version=latest,
        created_by=item.created_by,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def agent_detail(item: AgentORM) -> AgentDetail:
    return AgentDetail(
        **agent_view(item).model_dump(),
        versions=[version_view(version) for version in sorted(item.versions, key=lambda x: x.version, reverse=True)],
    )


@dataclass(frozen=True)
class AgentRef:
    id: str
    version: int


class AgentService:
    def initialize(self) -> None:
        initialize_agent_store()
        self.seed_built_ins()

    def seed_built_ins(self) -> None:
        with SessionLocal() as session:
            repo = AgentRepository(session)
            for request in BUILT_INS:
                if repo.get_by_slug(request.slug or "") is None:
                    repo.create(request, actor="system", built_in=True, publish=True)

    def list(self) -> list[AgentView]:
        with SessionLocal() as session:
            repo = AgentRepository(session)
            return [agent_view(item) for item in repo.list()]

    def get(self, agent_id: str) -> AgentDetail | None:
        with SessionLocal() as session:
            item = AgentRepository(session).get(agent_id)
            return agent_detail(item) if item else None

    def get_by_slug(self, slug: str) -> AgentDetail | None:
        with SessionLocal() as session:
            item = AgentRepository(session).get_by_slug(slug)
            return agent_detail(item) if item else None

    def create(self, request: AgentCreate, *, actor: str) -> AgentDetail:
        with SessionLocal() as session:
            item = AgentRepository(session).create(request, actor=actor)
            return agent_detail(item)

    def update(self, agent_id: str, request: AgentUpdate) -> AgentDetail:
        with SessionLocal() as session:
            repo = AgentRepository(session)
            item = repo.get(agent_id)
            if item is None:
                raise KeyError("Agent 不存在")
            return agent_detail(repo.update(item, request))

    def create_version(self, agent_id: str, patch: AgentVersionPatch, *, actor: str) -> AgentVersionView:
        with SessionLocal() as session:
            repo = AgentRepository(session)
            item = repo.get(agent_id)
            if item is None:
                raise KeyError("Agent 不存在")
            if item.status == "archived":
                raise ValueError("已归档 Agent 不能创建新 Version")
            return version_view(repo.create_version(item, patch, actor=actor))

    def publish(self, agent_id: str, version: int) -> AgentDetail:
        with SessionLocal() as session:
            repo = AgentRepository(session)
            item = repo.get(agent_id)
            if item is None:
                raise KeyError("Agent 不存在")
            return agent_detail(repo.publish(item, version))

    def archive(self, agent_id: str) -> AgentDetail:
        with SessionLocal() as session:
            repo = AgentRepository(session)
            item = repo.get(agent_id)
            if item is None:
                raise KeyError("Agent 不存在")
            if item.built_in:
                raise ValueError("Built-in Agent 不能归档")
            return agent_detail(repo.archive(item))

    def published_version(self, agent_id: str) -> AgentVersionView:
        detail = self.get(agent_id)
        if detail is None:
            raise KeyError("Agent 不存在")
        if detail.status != "published" or detail.published_version is None:
            raise ValueError("Agent 尚未发布")
        version = next((item for item in detail.versions if item.version == detail.published_version), None)
        if version is None:
            raise RuntimeError("Published Version 不存在")
        return version

    def builtin_ref(self, agent_type: str) -> AgentRef | None:
        with SessionLocal() as session:
            item = AgentRepository(session).get_by_type(agent_type, built_in=True)
            if item is None or item.published_version is None:
                return None
            return AgentRef(item.id, item.published_version)


agent_service = AgentService()
