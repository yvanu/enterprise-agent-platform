"""Compatibility import. Data Agent models live in app.agents.data."""

from app.agents.data.models import AgentAnswer, AskRequest, QueryResult, SqlAttempt, SqlRequest

__all__ = ["AgentAnswer", "AskRequest", "QueryResult", "SqlAttempt", "SqlRequest"]
