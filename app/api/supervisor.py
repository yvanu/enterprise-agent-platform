from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from app.agents.data.agent import DataAgent
from app.agents.supervisor.agent import SupervisorAgent
from app.agents.supervisor.models import IncidentAnswer, IncidentRequest
from app.api.data import get_database, llm
from app.api.knowledge import agent as knowledge_agent
from app.api.ops import agent as ops_agent
from app.platform.auth import Identity, current_identity, require_roles
from app.platform.llm import LLMNotConfiguredError
from app.platform.runs import start_run


router = APIRouter(
    prefix="/api/v1/supervisor",
    tags=["supervisor"],
    dependencies=[Depends(require_roles("operator", "admin"))],
)


@router.post("/investigate", response_model=IncidentAnswer)
def investigate(
    request: IncidentRequest,
    identity: Annotated[Identity, Depends(current_identity)],
) -> IncidentAnswer:
    run = start_run("supervisor")
    try:
        agent = SupervisorAgent(
            DataAgent(get_database(request.source), llm),
            knowledge_agent,
            ops_agent,
            llm,
        )
        answer = agent.investigate(request.question, role=identity.role)
        run.success(answer.trace)
        return answer
    except LLMNotConfiguredError as exc:
        run.error(exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        run.error(exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
