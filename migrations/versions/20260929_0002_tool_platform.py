"""tool platform

Revision ID: 20260929_0002
Revises: 20260929_0001
Create Date: 2026-09-29
"""

from alembic import op
import sqlalchemy as sa


revision = "20260929_0002"
down_revision = "20260929_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tools",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("key", sa.String(length=160), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("namespace", sa.String(length=80), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False, server_default="builtin"),
        sa.Column("type", sa.String(length=40), nullable=False, server_default="builtin"),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("risk", sa.String(length=20), nullable=False),
        sa.Column("approval_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("input_schema", sa.JSON(), nullable=False),
        sa.Column("output_schema", sa.JSON(), nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("key"),
    )
    op.create_index("ix_tools_key", "tools", ["key"])
    op.create_index("ix_tools_namespace", "tools", ["namespace"])

    op.create_table(
        "agent_tools",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("agent_version_id", sa.String(length=36), sa.ForeignKey("agent_versions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("tool_id", sa.String(length=36), sa.ForeignKey("tools.id", ondelete="CASCADE"), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("agent_version_id", "tool_id", name="uq_agent_version_tool"),
    )
    op.create_index("ix_agent_tools_agent_version_id", "agent_tools", ["agent_version_id"])
    op.create_index("ix_agent_tools_tool_id", "agent_tools", ["tool_id"])


def downgrade() -> None:
    op.drop_index("ix_agent_tools_tool_id", table_name="agent_tools")
    op.drop_index("ix_agent_tools_agent_version_id", table_name="agent_tools")
    op.drop_table("agent_tools")
    op.drop_index("ix_tools_namespace", table_name="tools")
    op.drop_index("ix_tools_key", table_name="tools")
    op.drop_table("tools")
