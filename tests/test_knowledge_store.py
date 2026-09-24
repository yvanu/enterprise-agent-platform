from app.agents.knowledge.store import KnowledgeStore


def _embed(texts: list[str]) -> list[list[float]]:
    return [[1.0, 0.0] if "雷达" in text else [0.0, 1.0] for text in texts]


def test_vector_search_returns_closest_document(tmp_path):
    store = KnowledgeStore(str(tmp_path / "knowledge.db"))
    radar_id = store.add_document("雷达资料", "雷达数据验收要求包含完整性检查。", _embed)
    store.add_document("海洋资料", "海温与盐度数据需要校验时间范围。", _embed)

    result = store.search("雷达怎么验收", _embed, top_k=1)

    assert result[0]["document_id"] == radar_id
    assert result[0]["title"] == "雷达资料"
