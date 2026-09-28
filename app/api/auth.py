from typing import Annotated

from fastapi import APIRouter, Depends

from app.platform.auth import Identity, current_identity


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.get("/me", response_model=Identity)
def me(identity: Annotated[Identity, Depends(current_identity)]) -> Identity:
    return identity
