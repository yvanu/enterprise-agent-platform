from fastapi import APIRouter, HTTPException, Query

from app.agents.data.agent import DataAgent
from app.agents.data.models import (
    AgentAnswer,
    AskRequest,
    DataSourceInfo,
    QueryResult,
    SqlRequest,
)
from app.core.config import get_settings
from app.db.engine import Database
from app.db.introspection import describe_schema
from app.platform.llm import LLMNotConfiguredError, OpenAICompatibleLLM


router = APIRouter(prefix="/api/v1/data", tags=["data"])
settings = get_settings()
llm = OpenAICompatibleLLM(settings)
db = Database(settings)
_databases: dict[str, Database] = {"default": db}


def get_database(source: str) -> Database:
    if source in _databases:
        return _databases[source]

    config = settings.data_sources.get(source)
    if not config:
        raise ValueError(f"未知数据源: {source}")

    database = Database(settings, url=config.url, schema=config.schema_name)
    _databases[source] = database
    return database


@router.get("/sources", response_model=list[DataSourceInfo])
def sources() -> list[DataSourceInfo]:
    result = [DataSourceInfo(name="default", schema_name=settings.database_schema)]
    result.extend(
        DataSourceInfo(name=name, schema_name=config.schema_name)
        for name, config in settings.data_sources.items()
        if name != "default"
    )
    return result


@router.get("/schema")
def schema(source: str = Query("default")) -> dict:
    try:
        database = get_database(source)
        return describe_schema(database.engine, database.schema)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/sql", response_model=QueryResult)
def execute_sql(request: SqlRequest) -> QueryResult:
    try:
        return get_database(request.source).execute_readonly(request.sql)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/ask", response_model=AgentAnswer)
def ask(request: AskRequest) -> AgentAnswer:
    try:
        return DataAgent(get_database(request.source), llm).ask(request.question)
    except LLMNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
