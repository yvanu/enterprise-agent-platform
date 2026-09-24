import json
import math
import sqlite3
from pathlib import Path
from typing import Callable


EmbeddingFn = Callable[[list[str]], list[list[float]]]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


def _chunks(content: str, size: int = 1000) -> list[str]:
    paragraphs = [p.strip() for p in content.splitlines() if p.strip()]
    chunks: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n{paragraph}".strip()
        if len(candidate) <= size:
            current = candidate
            continue
        if current:
            chunks.append(current)
        current = paragraph
    if current:
        chunks.append(current)
    return chunks or [content[:size]]


class KnowledgeStore:
    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS knowledge_chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding TEXT NOT NULL
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    def add_document(self, title: str, content: str, embed: EmbeddingFn) -> int:
        chunks = _chunks(content)
        vectors = embed(chunks)
        if len(vectors) != len(chunks):
            raise ValueError("Embedding 数量与文档分块数量不一致")

        with self._connect() as conn:
            document_id = int(
                conn.execute(
                    "SELECT COALESCE(MAX(document_id), 0) + 1 FROM knowledge_chunks"
                ).fetchone()[0]
            )
            conn.executemany(
                """
                INSERT INTO knowledge_chunks
                (document_id, title, chunk_index, content, embedding)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (document_id, title, i, chunk, json.dumps(vector))
                    for i, (chunk, vector) in enumerate(zip(chunks, vectors))
                ],
            )
        return document_id

    def search(self, query: str, embed: EmbeddingFn, top_k: int = 5) -> list[dict]:
        query_vector = embed([query])[0]
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT document_id, title, chunk_index, content, embedding FROM knowledge_chunks"
            ).fetchall()

        # ponytail: O(n) vector scan; replace with pgvector/Vectorize when corpus size makes it measurable.
        scored = [
            {
                "document_id": row[0],
                "title": row[1],
                "chunk_index": row[2],
                "text": row[3],
                "score": _cosine(query_vector, json.loads(row[4])),
            }
            for row in rows
        ]
        return sorted(scored, key=lambda item: item["score"], reverse=True)[:top_k]
