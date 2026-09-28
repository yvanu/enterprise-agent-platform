from fastapi import APIRouter, File, HTTPException, UploadFile

from app.agents.knowledge.agent import KnowledgeAgent
from app.agents.knowledge.models import AskRequest, DocumentRequest, KnowledgeAnswer
from app.agents.knowledge.parser import extract_text
from app.agents.knowledge.store import KnowledgeStore
from app.core.config import get_settings
from app.platform.approvals import approval_store
from app.platform.llm import LLMNotConfiguredError, OpenAICompatibleLLM
from app.platform.runs import start_run


router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])
settings = get_settings()
agent = KnowledgeAgent(
    KnowledgeStore(settings.knowledge_db_path),
    OpenAICompatibleLLM(settings),
    settings.knowledge_top_k,
)


@router.get("/documents")
def documents() -> list[dict]:
    return agent.documents()


@router.delete("/documents/{document_id}")
def delete_document(document_id: int, approval_id: int) -> dict[str, int]:
    if not any(item["document_id"] == document_id for item in agent.documents()):
        raise HTTPException(status_code=404, detail="文档不存在")

    try:
        approval_store.consume(
            approval_id,
            agent="knowledge",
            tool="document_delete",
            target=f"document:{document_id}",
        )
        if not agent.delete_document(document_id, approved=True):
            raise HTTPException(status_code=404, detail="文档不存在")
        return {"deleted_document_id": document_id}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/documents")
def add_document(request: DocumentRequest) -> dict[str, int]:
    try:
        return {"document_id": agent.add_document(request.title, request.content)}
    except LLMNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/documents/upload")
async def upload_document(file: UploadFile = File(...)) -> dict[str, int | str]:
    data = await file.read(settings.knowledge_max_upload_bytes + 1)
    if len(data) > settings.knowledge_max_upload_bytes:
        raise HTTPException(status_code=413, detail="文件超过知识库上传大小限制")

    try:
        content = extract_text(file.filename or "document.txt", data)
        document_id = agent.add_document(file.filename or "未命名文档", content)
        return {"document_id": document_id, "filename": file.filename or "未命名文档"}
    except LLMNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/ask", response_model=KnowledgeAnswer)
def ask(request: AskRequest) -> KnowledgeAnswer:
    run = start_run("knowledge")
    try:
        answer = agent.ask(request.question)
        run.success(answer.trace)
        return answer
    except LLMNotConfiguredError as exc:
        run.error(exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        run.error(exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
