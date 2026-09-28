from typing import Literal

from pydantic import BaseModel


class ToolPolicy(BaseModel):
    name: str
    agent: Literal["data", "knowledge", "ops"]
    risk: Literal["low", "medium", "high"]
    mode: Literal["read", "write"]
    approval_required: bool = False


POLICIES = [
    ToolPolicy(name="schema", agent="data", risk="low", mode="read"),
    ToolPolicy(name="readonly_sql", agent="data", risk="low", mode="read"),
    ToolPolicy(name="report", agent="data", risk="low", mode="read"),
    ToolPolicy(name="document_ingest", agent="knowledge", risk="medium", mode="write"),
    ToolPolicy(name="vector_search", agent="knowledge", risk="low", mode="read"),
    ToolPolicy(name="snapshot", agent="ops", risk="low", mode="read"),
    ToolPolicy(name="log_tail", agent="ops", risk="low", mode="read"),
    ToolPolicy(name="prometheus", agent="ops", risk="low", mode="read"),
    ToolPolicy(name="docker_ps", agent="ops", risk="low", mode="read"),
    ToolPolicy(name="kubernetes_pods", agent="ops", risk="low", mode="read"),
]


def tool_policies(agent: str | None = None) -> list[ToolPolicy]:
    if agent is None:
        return POLICIES
    return [policy for policy in POLICIES if policy.agent == agent]
