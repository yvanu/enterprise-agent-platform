import json
import sqlite3
from pathlib import Path
from time import perf_counter

from pydantic import BaseModel

from app.core.config import get_settings
from app.platform.models import TraceStep
from app.platform.observability import current_request_context, log_event


class RunRecord(BaseModel):
    id: int
    agent: str
    status: str
    duration_ms: int
    trace: list[TraceStep]
    error_type: str | None = None
    request_id: str | None = None
    correlation_id: str | None = None
    agent_id: str | None = None
    agent_version: int | None = None
    created_at: str


class RunStore:
    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS agent_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent TEXT NOT NULL,
                    status TEXT NOT NULL,
                    duration_ms INTEGER NOT NULL,
                    trace_json TEXT NOT NULL,
                    error_type TEXT,
                    request_id TEXT,
                    correlation_id TEXT,
                    agent_id TEXT,
                    agent_version INTEGER,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            columns = {
                row[1]
                for row in conn.execute("PRAGMA table_info(agent_runs)").fetchall()
            }
            if "request_id" not in columns:
                conn.execute("ALTER TABLE agent_runs ADD COLUMN request_id TEXT")
            if "correlation_id" not in columns:
                conn.execute("ALTER TABLE agent_runs ADD COLUMN correlation_id TEXT")
            if "agent_id" not in columns:
                conn.execute("ALTER TABLE agent_runs ADD COLUMN agent_id TEXT")
            if "agent_version" not in columns:
                conn.execute("ALTER TABLE agent_runs ADD COLUMN agent_version INTEGER")

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def record(
        self,
        *,
        agent: str,
        status: str,
        duration_ms: int,
        trace: list[TraceStep] | None = None,
        error_type: str | None = None,
        request_id: str | None = None,
        correlation_id: str | None = None,
        agent_id: str | None = None,
        agent_version: int | None = None,
    ) -> int:
        payload = json.dumps(
            [step.model_dump() for step in (trace or [])],
            ensure_ascii=False,
        )
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO agent_runs
                (
                    agent, status, duration_ms, trace_json, error_type,
                    request_id, correlation_id, agent_id, agent_version
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    agent,
                    status,
                    duration_ms,
                    payload,
                    error_type,
                    request_id,
                    correlation_id,
                    agent_id,
                    agent_version,
                ),
            )
        return int(cursor.lastrowid)

    @staticmethod
    def _record(row: tuple) -> RunRecord:
        return RunRecord(
            id=row[0],
            agent=row[1],
            status=row[2],
            duration_ms=row[3],
            trace=[TraceStep(**item) for item in json.loads(row[4])],
            error_type=row[5],
            request_id=row[6],
            correlation_id=row[7],
            agent_id=row[8],
            agent_version=row[9],
            created_at=row[10],
        )

    def get(self, run_id: int) -> RunRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, agent, status, duration_ms, trace_json, error_type,
                       request_id, correlation_id, agent_id, agent_version,
                       created_at
                FROM agent_runs
                WHERE id = ?
                """,
                (run_id,),
            ).fetchone()
        return self._record(row) if row else None

    def list(self, limit: int = 50, agent: str | None = None) -> list[RunRecord]:
        limit = max(1, min(limit, 200))
        sql = """
            SELECT id, agent, status, duration_ms, trace_json, error_type,
                   request_id, correlation_id, agent_id, agent_version,
                   created_at
            FROM agent_runs
        """
        params: list[object] = []
        if agent:
            sql += " WHERE agent = ?"
            params.append(agent)
        sql += " ORDER BY id DESC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()

        return [self._record(row) for row in rows]


run_store = RunStore(get_settings().platform_db_path)


class RunTimer:
    def __init__(
        self,
        agent: str,
        *,
        agent_id: str | None = None,
        agent_version: int | None = None,
    ):
        self.agent = agent
        self.agent_id = agent_id
        self.agent_version = agent_version
        self.started = perf_counter()
        self.request_id, self.correlation_id = current_request_context()

    def _duration_ms(self) -> int:
        return round((perf_counter() - self.started) * 1000)

    def success(self, trace: list[TraceStep]) -> int:
        duration_ms = self._duration_ms()
        run_id = run_store.record(
            agent=self.agent,
            status="ok",
            duration_ms=duration_ms,
            trace=trace,
            request_id=self.request_id,
            correlation_id=self.correlation_id,
            agent_id=self.agent_id,
            agent_version=self.agent_version,
        )
        log_event(
            "agent_run",
            run_id=run_id,
            agent=self.agent,
            status="ok",
            duration_ms=duration_ms,
            request_id=self.request_id,
            correlation_id=self.correlation_id,
            agent_id=self.agent_id,
            agent_version=self.agent_version,
        )
        return run_id

    def awaiting_approval(self, trace: list[TraceStep]) -> int:
        duration_ms = self._duration_ms()
        run_id = run_store.record(
            agent=self.agent,
            status="waiting_approval",
            duration_ms=duration_ms,
            trace=trace,
            request_id=self.request_id,
            correlation_id=self.correlation_id,
            agent_id=self.agent_id,
            agent_version=self.agent_version,
        )
        log_event("agent_run", run_id=run_id, agent=self.agent,
                  status="waiting_approval", duration_ms=duration_ms,
                  agent_id=self.agent_id, agent_version=self.agent_version)
        return run_id

    def error(self, exc: Exception) -> int:
        duration_ms = self._duration_ms()
        run_id = run_store.record(
            agent=self.agent,
            status="error",
            duration_ms=duration_ms,
            error_type=type(exc).__name__,
            request_id=self.request_id,
            correlation_id=self.correlation_id,
            agent_id=self.agent_id,
            agent_version=self.agent_version,
        )
        log_event(
            "agent_run",
            run_id=run_id,
            agent=self.agent,
            status="error",
            duration_ms=duration_ms,
            error_type=type(exc).__name__,
            request_id=self.request_id,
            correlation_id=self.correlation_id,
            agent_id=self.agent_id,
            agent_version=self.agent_version,
        )
        return run_id


def start_run(
    agent: str,
    *,
    agent_id: str | None = None,
    agent_version: int | None = None,
) -> RunTimer:
    if agent_id is None or agent_version is None:
        try:
            from app.modules.agents.service import agent_service

            ref = agent_service.builtin_ref(agent)
            if ref is not None:
                agent_id = agent_id or ref.id
                agent_version = agent_version or ref.version
        except Exception:
            # Run recording must stay available during bootstrap and migrations.
            pass
    return RunTimer(agent, agent_id=agent_id, agent_version=agent_version)
