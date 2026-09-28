from typing import Annotated, Callable, Literal

from fastapi import Depends, Header, HTTPException
from pydantic import BaseModel

from app.core.config import get_settings


Role = Literal["user", "operator", "approver", "admin"]
ROLES = {"user", "operator", "approver", "admin"}
settings = get_settings()


class Identity(BaseModel):
    username: str
    role: Role


def parse_identity(value: str) -> Identity:
    try:
        username, role = value.split(":", 1)
    except ValueError as exc:
        raise ValueError("AUTH_TOKENS 值必须使用 username:role 格式") from exc
    if not username or role not in ROLES:
        raise ValueError("AUTH_TOKENS 包含无效用户或角色")
    return Identity(username=username, role=role)


def current_identity(
    authorization: Annotated[str | None, Header()] = None,
) -> Identity:
    if not settings.auth_enabled:
        return Identity(username="development", role="admin")

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="缺少 Bearer Token")

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
