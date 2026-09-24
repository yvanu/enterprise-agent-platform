from fastapi import APIRouter, HTTPException

from app.agents.data.agent import DataAgent
from app.agents.data.models import AgentAnswer, AskRequest, QueryResult, SqlRequest
from app.core.config import get_settings
from app.db.engine import Database
from app.db.introspection import describe_schema
from app.platform.llm import LLMNotConfiguredError, OpenAICompatibleLLM


router = APIRouter(prefix="/api/v1/data", tags=["data"])
settings = get_settings()
db = Database(settings)
agent = DataAgent(db, OpenAICompatibleLLM(settings))


@router.get("/schema")
def schema() -> dict:
    return describe_schema(db.engine, settings.database_schema)


@router.post("/sql", response_model=QueryResult)
def execute_sql(request: SqlRequest) -> QueryResult:
    try:
        return db.execute_readonly(request.sql)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/ask", response_model=AgentAnswer)
def ask(request: AskRequest) -> AgentAnswer:
    try:
        return agent.ask(request.question)
    except LLMNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
