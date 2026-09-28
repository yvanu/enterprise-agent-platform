from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.platform.auth import (
    SESSION_COOKIE,
    Identity,
    create_console_session,
    current_identity,
    remove_console_session,
    settings,
)


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=1, max_length=500)


class LoginResponse(BaseModel):
    identity: Identity


@router.get("/status")
def status() -> dict:
    return {
        "auth_enabled": settings.auth_enabled,
        "console_login_enabled": True,
    }


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest, request: Request, response: Response) -> LoginResponse:
    try:
        session_token, identity = create_console_session(
            payload.username,
            payload.password,
        )
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    forwarded_proto = request.headers.get("x-forwarded-proto", "")
    response.set_cookie(
        SESSION_COOKIE,
        session_token,
        max_age=settings.session_max_age_seconds,
        httponly=True,
        secure=request.url.scheme == "https" or forwarded_proto == "https",
        samesite="lax",
        path="/",
    )
    return LoginResponse(identity=identity)


@router.post("/logout")
def logout(
    response: Response,
    eap_session: Annotated[str | None, Cookie()] = None,
) -> dict[str, bool]:
    remove_console_session(eap_session)
    response.delete_cookie(SESSION_COOKIE, path="/", samesite="lax")
    return {"ok": True}


@router.get("/me", response_model=Identity)
def me(identity: Annotated[Identity, Depends(current_identity)]) -> Identity:
    return identity
