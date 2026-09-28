from app.agents.knowledge.agent import KnowledgeAgent
from app.agents.knowledge.store import KnowledgeStore


def _embed(texts: list[str]) -> list[list[float]]:
    return [[1.0, 0.0] if "雷达" in text else [0.0, 1.0] for text in texts]


class _LLM:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return _embed(texts)

    def chat(self, messages):
        return "根据资料，需要检查完整性。[来源 1]"


def test_vector_search_returns_closest_document(tmp_path):
    store = KnowledgeStore(str(tmp_path / "knowledge.db"))
    radar_id = store.add_document("雷达资料", "雷达数据验收要求包含完整性检查。", _embed)
    store.add_document("海洋资料", "海温与盐度数据需要校验时间范围。", _embed)

    result = store.search("雷达怎么验收", _embed, top_k=1)

    assert result[0]["document_id"] == radar_id
    assert result[0]["title"] == "雷达资料"


def test_knowledge_agent_returns_trace(tmp_path):
    agent = KnowledgeAgent(KnowledgeStore(str(tmp_path / "knowledge.db")), _LLM(), top_k=1)
    agent.add_document("雷达资料", "雷达数据验收要求包含完整性检查。")

    answer = agent.ask("怎么验收雷达资料？")

    assert [step.name for step in answer.trace] == ["knowledge_search", "answer_with_context"]


def test_document_catalog(tmp_path):
    store = KnowledgeStore(str(tmp_path / "knowledge.db"))
    first = store.add_document("雷达资料", "雷达数据验收要求包含完整性检查。", _embed)
    second = store.add_document("海洋资料", "海温与盐度数据需要校验时间范围。", _embed)

    documents = store.list_documents()

    assert [item["document_id"] for item in documents] == [second, first]
    assert documents[0]["title"] == "海洋资料"
    assert documents[0]["chunks"] == 1


def test_document_delete_requires_approved_tool(tmp_path):
    agent = KnowledgeAgent(KnowledgeStore(str(tmp_path / "knowledge.db")), _LLM(), top_k=1)
    document_id = agent.add_document("雷达资料", "雷达数据验收要求包含完整性检查。")

    try:
        agent.delete_document(document_id)
        assert False, "delete should require approval"
    except PermissionError:
        pass

    assert agent.delete_document(document_id, approved=True) is True
    assert agent.documents() == []


def test_document_update_increments_version_and_metadata(tmp_path):
    store = KnowledgeStore(str(tmp_path / "knowledge.db"))
    document_id = store.add_document(
        "雷达资料",
        "雷达数据验收要求包含完整性检查。",
        _embed,
        tags=["雷达"],
        allowed_roles=["operator", "admin"],
    )

    version = store.update_document(
        document_id,
        "雷达资料 v2",
        "雷达数据验收还需要检查时间范围。",
        _embed,
        tags=["雷达", "验收"],
        allowed_roles=["operator"],
    )

    assert version == 2
    document = store.list_documents(role="operator")[0]
    assert document["version"] == 2
    assert document["tags"] == ["雷达", "验收"]
    assert document["allowed_roles"] == ["operator"]
    assert store.list_documents(role="user") == []


def test_role_filtered_retrieval(tmp_path):
    store = KnowledgeStore(str(tmp_path / "knowledge.db"))
    store.add_document(
        "管理员资料",
        "雷达内部资料。",
        _embed,
        allowed_roles=["admin"],
    )

    assert store.search("雷达", _embed, role="user") == []
    assert store.search("雷达", _embed, role="admin")[0]["title"] == "管理员资料"
