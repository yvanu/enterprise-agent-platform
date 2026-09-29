from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator, Literal

from pydantic import BaseModel

from app.modules.tools.catalog import BUILTIN_TOOLS


class ToolPolicy(BaseModel):
    id: str | None = None
    key: str = ""
    name: str
    agent: str
    description: str = ""
    provider: str = "builtin"
    type: str = "builtin"
    risk: Literal["low", "medium", "high"]
    mode: Literal["read", "write"]
    approval_required: bool = False
    enabled: bool = True


_STATIC_POLICIES = [
    ToolPolicy(
        key=item.key,
        name=item.name,
        agent=item.namespace,
        description=item.description,
        provider=item.provider,
        type=item.type,
        risk=item.risk,
        mode=item.mode,
        approval_required=item.approval_required,
    )
    for item in BUILTIN_TOOLS
]
POLICIES = _STATIC_POLICIES

_tool_context: ContextVar[tuple[str, int] | None] = ContextVar(
    "agent_tool_context",
    default=None,
)


class ToolPolicyError(PermissionError):
    pass


@contextmanager
def tool_execution_context(agent_id: str, agent_version: int) -> Iterator[None]:
    token = _tool_context.set((agent_id, agent_version))
    try:
        yield
    finally:
        _tool_context.reset(token)


@contextmanager
def builtin_tool_execution_context(agent_type: str) -> Iterator[None]:
    try:
        from app.modules.agents.service import agent_service

        ref = agent_service.builtin_ref(agent_type)
    except Exception:
        ref = None

    if ref is None:
        yield
        return

    with tool_execution_context(ref.id, ref.version):
        yield


def tool_policies(agent: str | None = None) -> list[ToolPolicy]:
    # Keep monkeypatch-based deterministic tests and bootstrap independent of DB state.
    if POLICIES is not _STATIC_POLICIES:
        return [item for item in POLICIES if agent is None or item.agent == agent]

    try:
        from app.modules.tools.service import tool_service

        tools = tool_service.list(namespace=agent, enabled_only=True)
        if tools:
            return [
                ToolPolicy(
                    id=item.id,
                    key=item.key,
                    name=item.name,
                    agent=item.namespace,
                    description=item.description,
                    provider=item.provider,
                    type=item.type,
                    risk=item.risk,
                    mode=item.mode,
                    approval_required=item.approval_required,
                    enabled=item.enabled,
                )
                for item in tools
            ]
    except Exception:
        pass

    return [item for item in _STATIC_POLICIES if agent is None or item.agent == agent]


def require_tool(
    agent: str,
    name: str,
    mode: str,
    *,
    approval_granted: bool = False,
) -> ToolPolicy:
    policy = next(
        (item for item in tool_policies(agent) if item.name == name),
        None,
    )
    if policy is None:
        raise ToolPolicyError(f"未注册的 Tool: {agent}.{name}")
    if policy.mode != mode:
        raise ToolPolicyError(
            f"Tool 模式不匹配: {agent}.{name} requires {policy.mode}, got {mode}"
        )

    execution = _tool_context.get()
    if execution is not None:
        agent_id, agent_version = execution
        try:
            from app.modules.tools.service import tool_service

            if not tool_service.is_assigned(agent_id, agent_version, policy.key):
                raise ToolPolicyError(f"Agent Version 未分配 Tool: {policy.key}")
        except ToolPolicyError:
            raise
        except Exception as exc:
            raise ToolPolicyError(
                f"Tool Assignment 校验失败: {policy.key}: {exc}"
            ) from exc

    if policy.approval_required and not approval_granted:
        raise ToolPolicyError(f"Tool 需要人工审批: {agent}.{name}")
    return policy
