from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.modules.agents.base import Base
from app.modules.agents.orm import utcnow


class ToolORM(Base):
    __tablename__ = "tools"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    key: Mapped[str] = mapped_column(String(160), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    namespace: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    provider: Mapped[str] = mapped_column(String(80), default="builtin", nullable=False)
    type: Mapped[str] = mapped_column(String(40), default="builtin", nullable=False)
    mode: Mapped[str] = mapped_column(String(20), nullable=False)
    risk: Mapped[str] = mapped_column(String(20), nullable=False)
    approval_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    input_schema: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    output_schema: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(default=30, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)

    assignments: Mapped[list["AgentToolORM"]] = relationship(back_populates="tool")


class AgentToolORM(Base):
    __tablename__ = "agent_tools"
    __table_args__ = (UniqueConstraint("agent_version_id", "tool_id", name="uq_agent_version_tool"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    agent_version_id: Mapped[str] = mapped_column(
        ForeignKey("agent_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    tool_id: Mapped[str] = mapped_column(
        ForeignKey("tools.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    config: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

    tool: Mapped[ToolORM] = relationship(back_populates="assignments")
