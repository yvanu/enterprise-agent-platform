"""Compatibility import. SQL safety belongs to the database boundary."""

from app.db.sql_guard import GuardedSql, UnsafeSqlError, guard_sql

__all__ = ["GuardedSql", "UnsafeSqlError", "guard_sql"]
