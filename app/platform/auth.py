from __future__ import annotations

from secrets import compare_digest, token_urlsafe
from time import monotonic
from typing import Annotated, Callable, Literal

from fastapi import Cookie, Depends, Header, HTTPException
from pydantic import BaseModel

from app.core.config import get_settings


Role = Literal["user", "operator", "approver", "admin"]
ROLES = {"user", "operator", "approver", "admin"}
SESSION_COOKIE = "eap_session"
settings = get_settings()


class Identity(BaseModel):
    username: str
    role: Role


_sessions: dict[str, tuple[Identity, float]] = {}


def parse_identity(value: str) -> Identity:
    try:
        username, role = value.split(":", 1)
    except ValueError as exc:
        raise ValueError("AUTH_TOKENS 值必须使用 username:role 格式") from exc
    if not username or role not in ROLES:
        raise ValueError("AUTH_TOKENS 包含无效用户或角色")
    return Identity(username=username, role=role)


def create_console_session(username: str, password: str) -> tuple[str, Identity]:
    expected_username = settings.console_username
    expected_password = settings.console_password.get_secret_value()
    if not compare_digest(username, expected_username) or not compare_digest(password, expected_password):
        raise ValueError("用户名或密码错误")

    identity = Identity(username=expected_username, role=settings.console_role)
    token = token_urlsafe(32)
    _sessions[token] = (identity, monotonic() + settings.session_max_age_seconds)
    return token, identity


def remove_console_session(token: str | None) -> None:
    if token:
        _sessions.pop(token, None)


def _session_identity(token: str | None) -> Identity | None:
    if not token:
        return None
    session = _sessions.get(token)
    if session is None:
        return None
    identity, expires_at = session
    if monotonic() >= expires_at:
        _sessions.pop(token, None)
        return None
    return identity


def current_identity(
    authorization: Annotated[str | None, Header()] = None,
    eap_session: Annotated[str | None, Cookie()] = None,
) -> Identity:
    if not settings.auth_enabled:
        return Identity(username="development", role="admin")

    session_identity = _session_identity(eap_session)
    if session_identity is not None:
        return session_identity

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="请先登录")

    token = authorization.removeprefix("Bearer ").strip()
    identity = settings.auth_tokens.get(token)
    if not identity:
        raise HTTPException(status_code=401, detail="无效 Bearer Token")
    try:
        return parse_identity(identity)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


def require_roles(*roles: Role) -> Callable:
    def dependency(
        identity: Annotated[Identity, Depends(current_identity)],
    ) -> Identity:
        if identity.role not in roles:
            raise HTTPException(status_code=403, detail="权限不足")
        return identity

    return dependency
