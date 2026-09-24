from fastapi import APIRouter, HTTPException

from app.agents.ops.agent import OpsAgent
from app.agents.ops.models import DiagnoseRequest, OpsAnswer, OpsSnapshot
from app.core.config import get_settings
from app.platform.llm import LLMNotConfiguredError, OpenAICompatibleLLM


router = APIRouter(prefix="/api/v1/ops", tags=["ops"])
agent = OpsAgent(OpenAICompatibleLLM(get_settings()))


@router.get("/snapshot", response_model=OpsSnapshot)
def snapshot() -> OpsSnapshot:
    return agent.snapshot()


@router.post("/diagnose", response_model=OpsAnswer)
def diagnose(request: DiagnoseRequest) -> OpsAnswer:
    try:
        return agent.diagnose(request.question)
    except LLMNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
