from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modules.agents.base import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AgentORM(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    type: Mapped[str] = mapped_column(String(32), default="generic", nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False, index=True)
    built_in: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published_version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    versions: Mapped[list["AgentVersionORM"]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan",
        order_by="AgentVersionORM.version",
    )


class AgentVersionORM(Base):
    __tablename__ = "agent_versions"
    __table_args__ = (UniqueConstraint("agent_id", "version", name="uq_agent_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False, index=True)

    instructions: Mapped[str] = mapped_column(Text, default="", nullable=False)
    model_provider: Mapped[str] = mapped_column(String(80), default="openai-compatible", nullable=False)
    model: Mapped[str] = mapped_column(String(160), default="", nullable=False)
    temperature: Mapped[float] = mapped_column(Float, default=0.2, nullable=False)
    max_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_steps: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)

    tool_config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    knowledge_config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    data_config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    guardrail_config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)

    created_by: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    agent: Mapped[AgentORM] = relationship(back_populates="versions")
