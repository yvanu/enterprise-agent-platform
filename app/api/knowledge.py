from fastapi import APIRouter, HTTPException

from app.agents.knowledge.agent import KnowledgeAgent
from app.agents.knowledge.models import AskRequest, DocumentRequest, KnowledgeAnswer
from app.agents.knowledge.store import KnowledgeStore
from app.core.config import get_settings
from app.platform.llm import LLMNotConfiguredError, OpenAICompatibleLLM


router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])
settings = get_settings()
agent = KnowledgeAgent(
    KnowledgeStore(settings.knowledge_db_path),
    OpenAICompatibleLLM(settings),
    settings.knowledge_top_k,
)


@router.post("/documents")
def add_document(request: DocumentRequest) -> dict[str, int]:
    try:
        return {"document_id": agent.add_document(request.title, request.content)}
    except LLMNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/ask", response_model=KnowledgeAnswer)
def ask(request: AskRequest) -> KnowledgeAnswer:
    try:
        return agent.ask(request.question)
    except LLMNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
