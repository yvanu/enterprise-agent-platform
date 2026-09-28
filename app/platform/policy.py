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
    ToolPolicy(name="document_catalog", agent="knowledge", risk="low", mode="read"),
    ToolPolicy(name="document_delete", agent="knowledge", risk="medium", mode="write", approval_required=True),
    ToolPolicy(name="vector_search", agent="knowledge", risk="low", mode="read"),
    ToolPolicy(name="snapshot", agent="ops", risk="low", mode="read"),
    ToolPolicy(name="log_tail", agent="ops", risk="low", mode="read"),
    ToolPolicy(name="prometheus", agent="ops", risk="low", mode="read"),
    ToolPolicy(name="docker_ps", agent="ops", risk="low", mode="read"),
    ToolPolicy(name="kubernetes_pods", agent="ops", risk="low", mode="read"),
    ToolPolicy(name="service_restart", agent="ops", risk="high", mode="write", approval_required=True),
]


class ToolPolicyError(PermissionError):
    pass


def tool_policies(agent: str | None = None) -> list[ToolPolicy]:
    if agent is None:
        return POLICIES
    return [policy for policy in POLICIES if policy.agent == agent]


def require_tool(
    agent: str,
    name: str,
    mode: str,
    *,
    approval_granted: bool = False,
) -> ToolPolicy:
    policy = next(
        (item for item in POLICIES if item.agent == agent and item.name == name),
        None,
    )
    if policy is None:
        raise ToolPolicyError(f"未注册的 Tool: {agent}.{name}")
    if policy.mode != mode:
        raise ToolPolicyError(
            f"Tool 模式不匹配: {agent}.{name} requires {policy.mode}, got {mode}"
        )
    if policy.approval_required and not approval_granted:
        raise ToolPolicyError(f"Tool 需要人工审批: {agent}.{name}")
    return policy
