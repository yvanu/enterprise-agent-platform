"""dynamic agent platform

Revision ID: 20260929_0001
Revises:
Create Date: 2026-09-29
"""

from alembic import op
import sqlalchemy as sa


revision = "20260929_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agents",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("type", sa.String(length=32), nullable=False, server_default="generic"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("built_in", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("published_version", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("slug"),
    )
    op.create_index("ix_agents_slug", "agents", ["slug"])
    op.create_index("ix_agents_type", "agents", ["type"])
    op.create_index("ix_agents_status", "agents", ["status"])

    op.create_table(
        "agent_versions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("agent_id", sa.String(length=36), sa.ForeignKey("agents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("instructions", sa.Text(), nullable=False, server_default=""),
        sa.Column("model_provider", sa.String(length=80), nullable=False, server_default="openai-compatible"),
        sa.Column("model", sa.String(length=160), nullable=False, server_default=""),
        sa.Column("temperature", sa.Float(), nullable=False, server_default="0.2"),
        sa.Column("max_tokens", sa.Integer(), nullable=True),
        sa.Column("max_steps", sa.Integer(), nullable=False, server_default="8"),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("tool_config", sa.JSON(), nullable=False),
        sa.Column("knowledge_config", sa.JSON(), nullable=False),
        sa.Column("data_config", sa.JSON(), nullable=False),
        sa.Column("guardrail_config", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("agent_id", "version", name="uq_agent_version"),
    )
    op.create_index("ix_agent_versions_agent_id", "agent_versions", ["agent_id"])
    op.create_index("ix_agent_versions_status", "agent_versions", ["status"])


def downgrade() -> None:
    op.drop_index("ix_agent_versions_status", table_name="agent_versions")
    op.drop_index("ix_agent_versions_agent_id", table_name="agent_versions")
    op.drop_table("agent_versions")
    op.drop_index("ix_agents_status", table_name="agents")
    op.drop_index("ix_agents_type", table_name="agents")
    op.drop_index("ix_agents_slug", table_name="agents")
    op.drop_table("agents")
