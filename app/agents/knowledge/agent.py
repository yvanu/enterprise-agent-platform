from app.agents.knowledge.models import KnowledgeAnswer, Source
from app.agents.knowledge.store import KnowledgeStore
from app.platform.llm import OpenAICompatibleLLM
from app.platform.models import TraceStep
from app.platform.policy import require_tool


class KnowledgeAgent:
    def __init__(self, store: KnowledgeStore, llm: OpenAICompatibleLLM, top_k: int = 5):
        self.store = store
        self.llm = llm
        self.top_k = top_k

    def add_document(
        self,
        title: str,
        content: str,
        *,
        tags: list[str] | None = None,
        allowed_roles: list[str] | None = None,
    ) -> int:
        require_tool("knowledge", "document_ingest", "write")
        return self.store.add_document(
            title,
            content,
            self.llm.embed,
            tags=tags,
            allowed_roles=allowed_roles,
        )

    def update_document(
        self,
        document_id: int,
        title: str,
        content: str,
        *,
        tags: list[str] | None = None,
        allowed_roles: list[str] | None = None,
    ) -> int | None:
        require_tool("knowledge", "document_ingest", "write")
        return self.store.update_document(
            document_id,
            title,
            content,
            self.llm.embed,
            tags=tags,
            allowed_roles=allowed_roles,
        )

    def documents(self, *, role: str | None = None) -> list[dict]:
        require_tool("knowledge", "document_catalog", "read")
        return self.store.list_documents(role=role)

    def delete_document(self, document_id: int, *, approved: bool = False) -> bool:
        require_tool(
            "knowledge",
            "document_delete",
            "write",
            approval_granted=approved,
        )
        return self.store.delete_document(document_id)

    def ask(self, question: str, *, role: str | None = None) -> KnowledgeAnswer:
        require_tool("knowledge", "vector_search", "read")
        sources = self.store.search(
            question,
            self.llm.embed,
            self.top_k,
            role=role,
        )
        trace = [TraceStep(kind="tool", name="knowledge_search", detail=f"{len(sources)} sources")]
        if not sources:
            return KnowledgeAnswer(question=question, answer="知识库中暂无可用资料。", sources=[], trace=trace)

        context = "\n\n".join(
            f"[来源 {i + 1}] {source['title']}\n{source['text']}"
            for i, source in enumerate(sources)
        )
        answer = self.llm.chat(
            [
                {
                    "role": "system",
                    "content": (
                        "你是企业知识 Agent。只能根据给定资料回答；资料不足时明确说明。"
                        "引用资料时使用 [来源 1]、[来源 2] 这样的标记。"
                    ),
                },
                {
                    "role": "user",
                    "content": f"问题：{question}\n\n资料：\n{context}",
                },
            ]
        )
        trace.append(TraceStep(kind="llm", name="answer_with_context"))
        return KnowledgeAnswer(
            question=question,
            answer=answer,
            sources=[Source(**source) for source in sources],
            trace=trace,
        )
