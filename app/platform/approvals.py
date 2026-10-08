import json
import sqlite3
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.platform.policy import ToolPolicyError, tool_policies


class ApprovalCreate(BaseModel):
    agent: str = Field(min_length=1, max_length=80)
    tool: str = Field(min_length=1, max_length=100)
    target: str = Field(min_length=1, max_length=500)
    reason: str = Field(default="", max_length=2000)
    arguments: dict | None = None
    agent_id: str | None = None
    agent_version: int | None = Field(default=None, ge=1)


class ApprovalDecision(BaseModel):
    decision: Literal["approved", "rejected"]


class ApprovalRecord(BaseModel):
    id: int
    agent: str
    tool: str
    target: str
    reason: str
    status: str
    requested_by: str | None = None
    actor: str | None = None
    consumed_by: str | None = None
    created_at: str
    decided_at: str | None = None
    arguments: dict | None = None
    agent_id: str | None = None
    agent_version: int | None = None


def canonical_arguments(arguments: dict) -> str:
    try:
        encoded = json.dumps(arguments, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("MCP 审批参数必须是有效 JSON") from exc
    if len(encoded.encode("utf-8")) > 16_384:
        raise ValueError("MCP 审批参数超过 16KB")
    return encoded


class ApprovalStore:
    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS approvals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent TEXT NOT NULL,
                    tool TEXT NOT NULL,
                    target TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    requested_by TEXT,
                    actor TEXT,
                    consumed_by TEXT,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    decided_at TEXT,
                    arguments_json TEXT,
                    agent_id TEXT,
                    agent_version INTEGER
                )
                """
            )
            columns = {
                row[1]
                for row in conn.execute("PRAGMA table_info(approvals)").fetchall()
            }
            if "requested_by" not in columns:
                conn.execute("ALTER TABLE approvals ADD COLUMN requested_by TEXT")
            if "consumed_by" not in columns:
                conn.execute("ALTER TABLE approvals ADD COLUMN consumed_by TEXT")
            for column, kind in (("arguments_json", "TEXT"), ("agent_id", "TEXT"),
                                 ("agent_version", "INTEGER")):
                if column not in columns:
                    conn.execute(f"ALTER TABLE approvals ADD COLUMN {column} {kind}")

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    @staticmethod
    def _record(row: tuple) -> ApprovalRecord:
        return ApprovalRecord(
            id=row[0],
            agent=row[1],
            tool=row[2],
            target=row[3],
            reason=row[4],
            status=row[5],
            requested_by=row[6],
            actor=row[7],
            consumed_by=row[8],
            created_at=row[9],
            decided_at=row[10],
            arguments=json.loads(row[11]) if row[11] is not None else None,
            agent_id=row[12],
            agent_version=row[13],
        )

    def create(self, request: ApprovalCreate, *, requester: str) -> ApprovalRecord:
        policy = next(
            (
                item
                for item in tool_policies(request.agent)
                if item.name == request.tool
            ),
            None,
        )
        if policy is None:
            raise ToolPolicyError(f"未注册的 Tool: {request.agent}.{request.tool}")
        if not policy.approval_required:
            raise ToolPolicyError(
                f"Tool 不需要人工审批: {request.agent}.{request.tool}"
            )

        argument_json = None
        if request.agent.startswith(("mcp.", "openapi.")):
            if (request.arguments is None or not request.agent_id
                    or request.agent_version is None):
                raise ValueError("MCP 审批必须指定 Agent Version 和具体 JSON 参数")
            from app.modules.agents.service import agent_service
            from app.modules.tools.service import tool_service
            published = agent_service.published_version(request.agent_id)
            if published.version != request.agent_version:
                raise PermissionError("MCP 审批的 Agent Version 不是当前发布版本")
            assignments = tool_service.list_version_tools(request.agent_id, request.agent_version)
            matches = [row for row in assignments if row.enabled and row.tool.enabled
                       and row.tool.provider in {"mcp", "openapi"} and row.tool.namespace == request.agent
                       and row.tool.name == request.tool
                       and request.target == f"tool:{row.tool.id}"]
            if len(matches) != 1:
                raise PermissionError("MCP Tool 未分配给指定 Agent Version")
            argument_json = canonical_arguments(request.arguments)
        elif request.arguments is not None or request.agent_id or request.agent_version:
            raise ValueError("非 MCP 工具不接受 MCP 审批参数")

        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO approvals
                (agent, tool, target, reason, requested_by, arguments_json, agent_id, agent_version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    request.agent, request.tool, request.target, request.reason,
                    requester, argument_json, request.agent_id, request.agent_version,
                ),
            )
            approval_id = int(cursor.lastrowid)
        record = self.get(approval_id)
        if record is None:
            raise RuntimeError("审批记录创建失败")
        return record

    def get(self, approval_id: int) -> ApprovalRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, agent, tool, target, reason, status,
                       requested_by, actor, consumed_by, created_at, decided_at,
                       arguments_json, agent_id, agent_version
                FROM approvals
                WHERE id = ?
                """,
                (approval_id,),
            ).fetchone()
        return self._record(row) if row else None

    def list(self, limit: int = 50) -> list[ApprovalRecord]:
        limit = max(1, min(limit, 200))
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, agent, tool, target, reason, status,
                       requested_by, actor, consumed_by, created_at, decided_at,
                       arguments_json, agent_id, agent_version
                FROM approvals
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._record(row) for row in rows]

    def decide(
        self,
        approval_id: int,
        decision: ApprovalDecision,
        *,
        actor: str,
    ) -> ApprovalRecord:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE approvals
                SET status = ?, actor = ?, decided_at = CURRENT_TIMESTAMP
                WHERE id = ? AND status = 'pending'
                """,
                (decision.decision, actor, approval_id),
            )
            if cursor.rowcount == 0:
                current = self.get(approval_id)
                if current is None:
                    raise KeyError("审批记录不存在")
                raise ValueError(f"审批状态不可变更: {current.status}")
        record = self.get(approval_id)
        if record is None:
            raise RuntimeError("审批记录读取失败")
        return record

    def consume(
        self,
        approval_id: int,
        *,
        agent: str,
        tool: str,
        target: str,
        actor: str,
        arguments: dict | None = None,
        agent_id: str | None = None,
        agent_version: int | None = None,
    ) -> None:
        if agent.startswith(("mcp.", "openapi.")):
            if arguments is None or not agent_id or agent_version is None:
                raise PermissionError("MCP 调用需要参数级审批")
            argument_json = canonical_arguments(arguments)
        else:
            argument_json = None
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE approvals
                SET status = 'consumed', consumed_by = ?
                WHERE id = ?
                  AND status = 'approved'
                  AND agent = ?
                  AND tool = ?
                  AND target = ?
                  AND arguments_json IS ?
                  AND agent_id IS ?
                  AND agent_version IS ?
                """,
                (actor, approval_id, agent, tool, target,
                 argument_json, agent_id, agent_version),
            )
            if cursor.rowcount == 0:
                record = self.get(approval_id)
                if record is None:
                    raise KeyError("审批记录不存在")
                raise PermissionError("审批未通过、已使用或与操作目标不匹配")


approval_store = ApprovalStore(get_settings().platform_db_path)
