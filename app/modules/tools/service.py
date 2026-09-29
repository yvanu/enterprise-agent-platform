from __future__ import annotations

from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.modules.agents.db import SessionLocal, initialize_agent_store
from app.modules.agents.orm import AgentVersionORM
from app.modules.agents.repository import AgentRepository
from app.modules.tools.catalog import BUILTIN_AGENT_TOOL_KEYS, BUILTIN_TOOLS
from app.modules.tools.models import AgentToolView, ToolView
from app.modules.tools.orm import AgentToolORM, ToolORM


def tool_view(item: ToolORM) -> ToolView:
    return ToolView(
        id=item.id,
        key=item.key,
        name=item.name,
        display_name=item.display_name,
        description=item.description,
        namespace=item.namespace,
        provider=item.provider,
        type=item.type,
        mode=item.mode,
        risk=item.risk,
        approval_required=item.approval_required,
        input_schema=item.input_schema or {},
        output_schema=item.output_schema or {},
        timeout_seconds=item.timeout_seconds,
        enabled=item.enabled,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def assignment_view(item: AgentToolORM) -> AgentToolView:
    return AgentToolView(
        id=item.id,
        agent_version_id=item.agent_version_id,
        tool=tool_view(item.tool),
        enabled=item.enabled,
        config=item.config or {},
        created_at=item.created_at,
    )


class ToolService:
    def initialize(self) -> None:
        initialize_agent_store()
        self.seed_builtin_tools()
        self.seed_builtin_assignments()

    @staticmethod
    def _version(session, agent_id: str, version: int) -> AgentVersionORM | None:
        return session.scalar(
            select(AgentVersionORM).where(
                AgentVersionORM.agent_id == agent_id,
                AgentVersionORM.version == version,
            )
        )

    def seed_builtin_tools(self) -> None:
        with SessionLocal() as session:
            for definition in BUILTIN_TOOLS:
                item = session.scalar(select(ToolORM).where(ToolORM.key == definition.key))
                if item is None:
                    item = ToolORM(id=str(uuid4()), key=definition.key)
                    session.add(item)
                item.name = definition.name
                item.display_name = definition.display_name
                item.description = definition.description
                item.namespace = definition.namespace
                item.provider = definition.provider
                item.type = definition.type
                item.mode = definition.mode
                item.risk = definition.risk
                item.approval_required = definition.approval_required
                item.input_schema = dict(definition.input_schema or {})
                item.output_schema = dict(definition.output_schema or {})
                item.timeout_seconds = definition.timeout_seconds
                item.enabled = True
            session.commit()

    def seed_builtin_assignments(self) -> None:
        with SessionLocal() as session:
            agents = AgentRepository(session)
            tools_by_key = {
                item.key: item
                for item in session.scalars(select(ToolORM).where(ToolORM.enabled.is_(True)))
            }
            for agent_type, keys in BUILTIN_AGENT_TOOL_KEYS.items():
                agent = agents.get_by_type(agent_type, built_in=True)
                if agent is None:
                    continue

                initial_version = self._version(session, agent.id, 1)
                if initial_version is None:
                    continue
                existing = session.scalar(
                    select(AgentToolORM.id)
                    .where(AgentToolORM.agent_version_id == initial_version.id)
                    .limit(1)
                )
                if existing is not None or not keys:
                    continue

                tool_ids = [tools_by_key[key].id for key in keys if key in tools_by_key]
                self._replace_in_session(
                    session,
                    agent.id,
                    1,
                    tool_ids,
                    allow_published=True,
                )

    def list(
        self,
        *,
        namespace: str | None = None,
        enabled_only: bool = False,
    ) -> list[ToolView]:
        with SessionLocal() as session:
            query = select(ToolORM)
            if namespace:
                query = query.where(ToolORM.namespace == namespace)
            if enabled_only:
                query = query.where(ToolORM.enabled.is_(True))
            items = session.scalars(query.order_by(ToolORM.namespace, ToolORM.name))
            return [tool_view(item) for item in items]

    def get(self, tool_id: str) -> ToolView | None:
        with SessionLocal() as session:
            item = session.get(ToolORM, tool_id)
            return tool_view(item) if item else None

    def list_version_tools(self, agent_id: str, version: int) -> list[AgentToolView]:
        with SessionLocal() as session:
            target = self._version(session, agent_id, version)
            if target is None:
                raise KeyError("Agent Version 不存在")
            rows = session.scalars(
                select(AgentToolORM)
                .options(selectinload(AgentToolORM.tool))
                .where(AgentToolORM.agent_version_id == target.id)
                .order_by(AgentToolORM.created_at, AgentToolORM.id)
            )
            return [assignment_view(item) for item in rows]

    def _replace_in_session(
        self,
        session,
        agent_id: str,
        version: int,
        tool_ids: list[str],
        *,
        allow_published: bool = False,
    ) -> list[AgentToolORM]:
        target = self._version(session, agent_id, version)
        if target is None:
            raise KeyError("Agent Version 不存在")
        if target.status != "draft" and not allow_published:
            raise ValueError("只能修改 Draft Version 的 Tool")

        unique_ids = list(dict.fromkeys(tool_ids))
        if unique_ids:
            tools = list(
                session.scalars(
                    select(ToolORM).where(
                        ToolORM.id.in_(unique_ids),
                        ToolORM.enabled.is_(True),
                    )
                )
            )
            if len(tools) != len(unique_ids):
                raise KeyError("包含不存在或已禁用的 Tool")

        session.execute(
            delete(AgentToolORM).where(AgentToolORM.agent_version_id == target.id)
        )
        for tool_id in unique_ids:
            session.add(
                AgentToolORM(
                    id=str(uuid4()),
                    agent_version_id=target.id,
                    tool_id=tool_id,
                    enabled=True,
                    config={},
                )
            )
        session.commit()
        return list(
            session.scalars(
                select(AgentToolORM)
                .options(selectinload(AgentToolORM.tool))
                .where(AgentToolORM.agent_version_id == target.id)
            )
        )

    def replace_version_tools(
        self,
        agent_id: str,
        version: int,
        tool_ids: list[str],
    ) -> list[AgentToolView]:
        with SessionLocal() as session:
            rows = self._replace_in_session(session, agent_id, version, tool_ids)
            return [assignment_view(item) for item in rows]

    def _clone_in_session(
        self,
        session,
        agent_id: str,
        from_version: int,
        to_version: int,
    ) -> None:
        source = self._version(session, agent_id, from_version)
        target = self._version(session, agent_id, to_version)
        if source is None or target is None:
            raise KeyError("Agent Version 不存在")

        rows = list(
            session.scalars(
                select(AgentToolORM).where(AgentToolORM.agent_version_id == source.id)
            )
        )
        session.execute(
            delete(AgentToolORM).where(AgentToolORM.agent_version_id == target.id)
        )
        for row in rows:
            session.add(
                AgentToolORM(
                    id=str(uuid4()),
                    agent_version_id=target.id,
                    tool_id=row.tool_id,
                    enabled=row.enabled,
                    config=dict(row.config or {}),
                )
            )
        session.commit()

    def clone_assignments(
        self,
        agent_id: str,
        from_version: int,
        to_version: int,
        *,
        session=None,
    ) -> None:
        if session is not None:
            self._clone_in_session(session, agent_id, from_version, to_version)
            return
        with SessionLocal() as owned_session:
            self._clone_in_session(
                owned_session,
                agent_id,
                from_version,
                to_version,
            )

    def is_assigned(self, agent_id: str, version: int, tool_key: str) -> bool:
        with SessionLocal() as session:
            target = self._version(session, agent_id, version)
            if target is None:
                return False
            return (
                session.scalar(
                    select(AgentToolORM.id)
                    .join(ToolORM, ToolORM.id == AgentToolORM.tool_id)
                    .where(
                        AgentToolORM.agent_version_id == target.id,
                        AgentToolORM.enabled.is_(True),
                        ToolORM.enabled.is_(True),
                        ToolORM.key == tool_key,
                    )
                    .limit(1)
                )
                is not None
            )


tool_service = ToolService()
