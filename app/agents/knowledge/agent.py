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

    def add_document(self, title: str, content: str) -> int:
        require_tool("knowledge", "document_ingest", "write")
        return self.store.add_document(title, content, self.llm.embed)

    def documents(self) -> list[dict]:
        require_tool("knowledge", "document_catalog", "read")
        return self.store.list_documents()

    def ask(self, question: str) -> KnowledgeAnswer:
        require_tool("knowledge", "vector_search", "read")
        sources = self.store.search(question, self.llm.embed, self.top_k)
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
