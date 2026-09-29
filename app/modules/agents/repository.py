from __future__ import annotations

import re
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.modules.agents.models import AgentCreate, AgentUpdate, AgentVersionPatch
from app.modules.agents.orm import AgentORM, AgentVersionORM


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or f"agent-{uuid4().hex[:8]}"


class AgentRepository:
    def __init__(self, session: Session):
        self.session = session

    def list(self) -> list[AgentORM]:
        return list(
            self.session.scalars(
                select(AgentORM).order_by(AgentORM.built_in.desc(), AgentORM.created_at.asc())
            )
        )

    def get(self, agent_id: str) -> AgentORM | None:
        return self.session.scalar(
            select(AgentORM)
            .options(selectinload(AgentORM.versions))
            .where(AgentORM.id == agent_id)
        )

    def get_by_slug(self, slug: str) -> AgentORM | None:
        return self.session.scalar(
            select(AgentORM)
            .options(selectinload(AgentORM.versions))
            .where(AgentORM.slug == slug)
        )

    def get_by_type(self, agent_type: str, built_in: bool = True) -> AgentORM | None:
        return self.session.scalar(
            select(AgentORM)
            .options(selectinload(AgentORM.versions))
            .where(AgentORM.type == agent_type, AgentORM.built_in == built_in)
            .order_by(AgentORM.created_at.asc())
        )

    def create(self, request: AgentCreate, *, actor: str, built_in: bool = False, publish: bool = False) -> AgentORM:
        base_slug = slugify(request.slug or request.name)
        slug = base_slug
        suffix = 2
        while self.get_by_slug(slug):
            slug = f"{base_slug}-{suffix}"
            suffix += 1

        agent = AgentORM(
            id=str(uuid4()),
            name=request.name,
            slug=slug,
            description=request.description,
            type=request.type,
            status="published" if publish else "draft",
            built_in=built_in,
            published_version=1 if publish else None,
            created_by=actor,
        )
        version_data = request.version.model_dump()
        version = AgentVersionORM(
            id=str(uuid4()),
            agent_id=agent.id,
            version=1,
            status="published" if publish else "draft",
            created_by=actor,
            **version_data,
        )
        if publish:
            from app.modules.agents.orm import utcnow
            version.published_at = utcnow()
        agent.versions.append(version)
        self.session.add(agent)
        self.session.commit()
        self.session.refresh(agent)
        return self.get(agent.id) or agent

    def update(self, agent: AgentORM, request: AgentUpdate) -> AgentORM:
        payload = request.model_dump(exclude_unset=True)
        for key, value in payload.items():
            setattr(agent, key, value)
        self.session.commit()
        return self.get(agent.id) or agent

    def next_version(self, agent_id: str) -> int:
        current = self.session.scalar(
            select(func.max(AgentVersionORM.version)).where(AgentVersionORM.agent_id == agent_id)
        )
        return int(current or 0) + 1

    def create_version(self, agent: AgentORM, patch: AgentVersionPatch, *, actor: str) -> AgentVersionORM:
        latest = max(agent.versions, key=lambda item: item.version)
        payload = {
            "instructions": latest.instructions,
            "model_provider": latest.model_provider,
            "model": latest.model,
            "temperature": latest.temperature,
            "max_tokens": latest.max_tokens,
            "max_steps": latest.max_steps,
            "timeout_seconds": latest.timeout_seconds,
            "tool_config": dict(latest.tool_config or {}),
            "knowledge_config": dict(latest.knowledge_config or {}),
            "data_config": dict(latest.data_config or {}),
            "guardrail_config": dict(latest.guardrail_config or {}),
        }
        payload.update(patch.model_dump(exclude_unset=True, exclude_none=True))
        version = AgentVersionORM(
            id=str(uuid4()),
            agent_id=agent.id,
            version=self.next_version(agent.id),
            status="draft",
            created_by=actor,
            **payload,
        )
        self.session.add(version)
        self.session.commit()
        self.session.refresh(version)
        return version

    def publish(self, agent: AgentORM, version_number: int) -> AgentORM:
        version = next((item for item in agent.versions if item.version == version_number), None)
        if version is None:
            raise KeyError("Agent Version 不存在")
        from app.modules.agents.orm import utcnow

        for item in agent.versions:
            if item.status == "published":
                item.status = "archived"
        version.status = "published"
        version.published_at = utcnow()
        agent.published_version = version.version
        agent.status = "published"
        self.session.commit()
        return self.get(agent.id) or agent

    def archive(self, agent: AgentORM) -> AgentORM:
        agent.status = "archived"
        self.session.commit()
        return self.get(agent.id) or agent
