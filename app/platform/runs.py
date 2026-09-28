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
                    request_id, correlation_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    agent,
                    status,
                    duration_ms,
                    payload,
                    error_type,
                    request_id,
                    correlation_id,
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
            created_at=row[8],
        )

    def get(self, run_id: int) -> RunRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, agent, status, duration_ms, trace_json, error_type,
                       request_id, correlation_id, created_at
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
                   request_id, correlation_id, created_at
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
    def __init__(self, agent: str):
        self.agent = agent
        self.started = perf_counter()
        self.request_id, self.correlation_id = current_request_context()

    def _duration_ms(self) -> int:
        return round((perf_counter() - self.started) * 1000)

    def success(self, trace: list[TraceStep]) -> None:
        duration_ms = self._duration_ms()
        run_id = run_store.record(
            agent=self.agent,
            status="ok",
            duration_ms=duration_ms,
            trace=trace,
            request_id=self.request_id,
            correlation_id=self.correlation_id,
        )
        log_event(
            "agent_run",
            run_id=run_id,
            agent=self.agent,
            status="ok",
            duration_ms=duration_ms,
            request_id=self.request_id,
            correlation_id=self.correlation_id,
        )

    def error(self, exc: Exception) -> None:
        duration_ms = self._duration_ms()
        run_id = run_store.record(
            agent=self.agent,
            status="error",
            duration_ms=duration_ms,
            error_type=type(exc).__name__,
            request_id=self.request_id,
            correlation_id=self.correlation_id,
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
        )


def start_run(agent: str) -> RunTimer:
    return RunTimer(agent)
