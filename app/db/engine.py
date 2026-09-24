from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from app.agent.models import QueryResult
from app.agent.sql_guard import guard_sql
from app.core.config import Settings


class Database:
    def __init__(self, settings: Settings):
        self.settings = settings

        if settings.database_url.startswith("sqlite:///"):
            raw_path = settings.database_url.removeprefix("sqlite:///")
            if raw_path and raw_path != ":memory:":
                Path(raw_path).parent.mkdir(parents=True, exist_ok=True)

        kwargs: dict[str, Any] = {"pool_pre_ping": True}
        if settings.database_url.startswith("sqlite:"):
            kwargs["connect_args"] = {"check_same_thread": False}

        self.engine: Engine = create_engine(settings.database_url, **kwargs)

    @property
    def dialect(self) -> str:
        name = self.engine.dialect.name
        if name in {"postgresql", "kingbase"}:
            return "postgres"
        if name == "sqlite":
            return "sqlite"
        return name

    def execute_readonly(self, sql: str) -> QueryResult:
        guarded = guard_sql(
            sql,
            max_rows=self.settings.sql_max_rows + 1,
            dialect=self.dialect,
        )

        with self.engine.begin() as conn:
            if self.engine.dialect.name == "postgresql":
                timeout_ms = max(1, int(self.settings.sql_timeout_seconds * 1000))
                conn.exec_driver_sql(f"SET LOCAL statement_timeout = {timeout_ms}")
                conn.exec_driver_sql("SET LOCAL transaction_read_only = on")

            result = conn.execute(text(guarded.executable))
            rows = [dict(row) for row in result.mappings().all()]

        truncated = len(rows) > self.settings.sql_max_rows
        visible_rows = rows[: self.settings.sql_max_rows]
        columns = list(result.keys())

        return QueryResult(
            columns=columns,
            rows=visible_rows,
            row_count=len(visible_rows),
            truncated=truncated,
        )
