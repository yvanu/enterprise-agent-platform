from fastapi import APIRouter, Query

from app.platform.policy import ToolPolicy, tool_policies


router = APIRouter(prefix="/api/v1/platform", tags=["platform"])


@router.get("/tools", response_model=list[ToolPolicy])
def tools(agent: str | None = Query(default=None)) -> list[ToolPolicy]:
    return tool_policies(agent)
