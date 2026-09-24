"""Compatibility import. Agent APIs are split by domain."""

from app.api.data import agent, db, router, settings

__all__ = ["agent", "db", "router", "settings"]
