import sqlite3
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.platform.policy import ToolPolicyError, tool_policies


class ApprovalCreate(BaseModel):
    agent: Literal["data", "knowledge", "ops"]
    tool: str = Field(min_length=1, max_length=100)
    target: str = Field(min_length=1, max_length=500)
    reason: str = Field(default="", max_length=2000)


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
                    decided_at TEXT
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

        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO approvals
                (agent, tool, target, reason, requested_by)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    request.agent,
                    request.tool,
                    request.target,
                    request.reason,
                    requester,
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
                       requested_by, actor, consumed_by, created_at, decided_at
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
                       requested_by, actor, consumed_by, created_at, decided_at
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
    ) -> None:
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
                """,
                (actor, approval_id, agent, tool, target),
            )
            if cursor.rowcount == 0:
                record = self.get(approval_id)
                if record is None:
                    raise KeyError("审批记录不存在")
                raise PermissionError("审批未通过、已使用或与操作目标不匹配")


approval_store = ApprovalStore(get_settings().platform_db_path)
