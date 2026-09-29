from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.agents.knowledge.agent import KnowledgeAgent
from app.agents.knowledge.models import AskRequest, DocumentRequest, KnowledgeAnswer
from app.agents.knowledge.parser import extract_text
from app.agents.knowledge.store import KnowledgeStore
from app.core.config import get_settings
from app.platform.approvals import approval_store
from app.platform.auth import Identity, ROLES, current_identity, require_roles
from app.platform.llm import LLMNotConfiguredError, OpenAICompatibleLLM
from app.platform.policy import builtin_tool_execution_context
from app.platform.runs import start_run


router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])
settings = get_settings()
agent = KnowledgeAgent(
    KnowledgeStore(settings.knowledge_db_path),
    OpenAICompatibleLLM(settings),
    settings.knowledge_top_k,
)


def _form_roles(value: str) -> list[str] | None:
    if not value.strip():
        return None
    roles = [item.strip() for item in value.split(",") if item.strip()]
    if any(role not in ROLES for role in roles):
        raise HTTPException(status_code=400, detail="allowed_roles 包含无效角色")
    return roles


@router.get("/documents")
def documents(
    identity: Annotated[Identity, Depends(current_identity)],
) -> list[dict]:
    with builtin_tool_execution_context("knowledge"):
        return agent.documents(role=identity.role)


@router.delete("/documents/{document_id}")
def delete_document(
    document_id: int,
    approval_id: int,
    identity: Annotated[Identity, Depends(require_roles("operator", "admin"))],
) -> dict[str, int]:
    with builtin_tool_execution_context("knowledge"):
        if not any(item["document_id"] == document_id for item in agent.documents()):
            raise HTTPException(status_code=404, detail="文档不存在")

    try:
        approval_store.consume(
            approval_id,
            agent="knowledge",
            tool="document_delete",
            target=f"document:{document_id}",
            actor=identity.username,
        )
        with builtin_tool_execution_context("knowledge"):
            if not agent.delete_document(document_id, approved=True):
                raise HTTPException(status_code=404, detail="文档不存在")
        return {"deleted_document_id": document_id}
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/documents")
def add_document(
    request: DocumentRequest,
    identity: Annotated[Identity, Depends(require_roles("operator", "admin"))],
) -> dict[str, int]:
    try:
        with builtin_tool_execution_context("knowledge"):
            return {
                "document_id": agent.add_document(
                    request.title,
                    request.content,
                    tags=request.tags,
                    allowed_roles=list(request.allowed_roles),
                )
            }
    except LLMNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/documents/upload")
async def upload_document(
    identity: Annotated[Identity, Depends(require_roles("operator", "admin"))],
    file: UploadFile = File(...),
    tags: str = Form(""),
    allowed_roles: str = Form(""),
) -> dict[str, int | str]:
    data = await file.read(settings.knowledge_max_upload_bytes + 1)
    if len(data) > settings.knowledge_max_upload_bytes:
        raise HTTPException(status_code=413, detail="文件超过知识库上传大小限制")

    try:
        content = extract_text(file.filename or "document.txt", data)
        with builtin_tool_execution_context("knowledge"):
            document_id = agent.add_document(
                file.filename or "未命名文档",
                content,
                tags=[item.strip() for item in tags.split(",") if item.strip()],
                allowed_roles=_form_roles(allowed_roles),
            )
        return {"document_id": document_id, "filename": file.filename or "未命名文档"}
    except LLMNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/documents/{document_id}")
def update_document(
    document_id: int,
    request: DocumentRequest,
    identity: Annotated[Identity, Depends(require_roles("operator", "admin"))],
) -> dict[str, int]:
    try:
        with builtin_tool_execution_context("knowledge"):
            version = agent.update_document(
                document_id,
                request.title,
                request.content,
                tags=request.tags,
                allowed_roles=list(request.allowed_roles),
            )
        if version is None:
            raise HTTPException(status_code=404, detail="文档不存在")
        return {"document_id": document_id, "version": version}
    except LLMNotConfiguredError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/ask", response_model=KnowledgeAnswer)
def ask(
    request: AskRequest,
    identity: Annotated[Identity, Depends(current_identity)],
) -> KnowledgeAnswer:
    run = start_run("knowledge")
    try:
        with builtin_tool_execution_context("knowledge"):
            answer = agent.ask(request.question, role=identity.role)
        run.success(answer.trace)
        return answer
    except LLMNotConfiguredError as exc:
        run.error(exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        run.error(exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
