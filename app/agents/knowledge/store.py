import json
import math
import sqlite3
from pathlib import Path
from typing import Callable


EmbeddingFn = Callable[[list[str]], list[list[float]]]
ALL_ROLES = ["user", "operator", "approver", "admin"]


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
                    embedding TEXT NOT NULL,
                    version INTEGER NOT NULL DEFAULT 1,
                    tags TEXT NOT NULL DEFAULT '[]',
                    allowed_roles TEXT NOT NULL DEFAULT '["user","operator","approver","admin"]'
                )
                """
            )
            columns = {
                row[1]
                for row in conn.execute("PRAGMA table_info(knowledge_chunks)").fetchall()
            }
            if "version" not in columns:
                conn.execute(
                    "ALTER TABLE knowledge_chunks ADD COLUMN version INTEGER NOT NULL DEFAULT 1"
                )
            if "tags" not in columns:
                conn.execute(
                    "ALTER TABLE knowledge_chunks ADD COLUMN tags TEXT NOT NULL DEFAULT '[]'"
                )
            if "allowed_roles" not in columns:
                conn.execute(
                    """ALTER TABLE knowledge_chunks
                    ADD COLUMN allowed_roles TEXT NOT NULL
                    DEFAULT '["user","operator","approver","admin"]'"""
                )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path)

    @staticmethod
    def _normalized_roles(allowed_roles: list[str] | None) -> list[str]:
        roles = list(dict.fromkeys(allowed_roles or ALL_ROLES))
        return roles or ALL_ROLES

    def _write_document(
        self,
        conn: sqlite3.Connection,
        *,
        document_id: int,
        title: str,
        content: str,
        embed: EmbeddingFn,
        version: int,
        tags: list[str] | None,
        allowed_roles: list[str] | None,
    ) -> None:
        chunks = _chunks(content)
        vectors = embed(chunks)
        if len(vectors) != len(chunks):
            raise ValueError("Embedding 数量与文档分块数量不一致")

        tags_json = json.dumps(list(dict.fromkeys(tags or [])), ensure_ascii=False)
        roles_json = json.dumps(
            self._normalized_roles(allowed_roles),
            ensure_ascii=False,
        )
        conn.executemany(
            """
            INSERT INTO knowledge_chunks
            (
                document_id, title, chunk_index, content, embedding,
                version, tags, allowed_roles
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    document_id,
                    title,
                    i,
                    chunk,
                    json.dumps(vector),
                    version,
                    tags_json,
                    roles_json,
                )
                for i, (chunk, vector) in enumerate(zip(chunks, vectors))
            ],
        )

    def add_document(
        self,
        title: str,
        content: str,
        embed: EmbeddingFn,
        *,
        tags: list[str] | None = None,
        allowed_roles: list[str] | None = None,
    ) -> int:
        with self._connect() as conn:
            document_id = int(
                conn.execute(
                    "SELECT COALESCE(MAX(document_id), 0) + 1 FROM knowledge_chunks"
                ).fetchone()[0]
            )
            self._write_document(
                conn,
                document_id=document_id,
                title=title,
                content=content,
                embed=embed,
                version=1,
                tags=tags,
                allowed_roles=allowed_roles,
            )
        return document_id

    def update_document(
        self,
        document_id: int,
        title: str,
        content: str,
        embed: EmbeddingFn,
        *,
        tags: list[str] | None = None,
        allowed_roles: list[str] | None = None,
    ) -> int | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT MAX(version), tags, allowed_roles
                FROM knowledge_chunks
                WHERE document_id = ?
                """,
                (document_id,),
            ).fetchone()
            if not row or row[0] is None:
                return None

            version = int(row[0]) + 1
            current_tags = json.loads(row[1]) if row[1] else []
            current_roles = json.loads(row[2]) if row[2] else ALL_ROLES
            conn.execute(
                "DELETE FROM knowledge_chunks WHERE document_id = ?",
                (document_id,),
            )
            self._write_document(
                conn,
                document_id=document_id,
                title=title,
                content=content,
                embed=embed,
                version=version,
                tags=tags if tags is not None else current_tags,
                allowed_roles=(
                    allowed_roles if allowed_roles is not None else current_roles
                ),
            )
        return version

    def search(
        self,
        query: str,
        embed: EmbeddingFn,
        top_k: int = 5,
        *,
        role: str | None = None,
    ) -> list[dict]:
        query_vector = embed([query])[0]
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT document_id, title, chunk_index, content, embedding,
                       version, tags, allowed_roles
                FROM knowledge_chunks
                """
            ).fetchall()

        scored = []
        for row in rows:
            allowed_roles = json.loads(row[7]) if row[7] else ALL_ROLES
            if role and role not in allowed_roles:
                continue
            scored.append(
                {
                    "document_id": row[0],
                    "title": row[1],
                    "chunk_index": row[2],
                    "text": row[3],
                    "score": _cosine(query_vector, json.loads(row[4])),
                    "version": row[5],
                    "tags": json.loads(row[6]) if row[6] else [],
                }
            )

        # ponytail: O(n) vector scan; replace with pgvector/Vectorize when corpus size makes it measurable.
        return sorted(scored, key=lambda item: item["score"], reverse=True)[:top_k]

    def list_documents(self, *, role: str | None = None) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT document_id, title, MAX(version), tags, allowed_roles,
                       COUNT(*) AS chunks
                FROM knowledge_chunks
                GROUP BY document_id, title, tags, allowed_roles
                ORDER BY document_id DESC
                """
            ).fetchall()

        documents = []
        for row in rows:
            allowed_roles = json.loads(row[4]) if row[4] else ALL_ROLES
            if role and role not in allowed_roles:
                continue
            documents.append(
                {
                    "document_id": row[0],
                    "title": row[1],
                    "version": row[2],
                    "tags": json.loads(row[3]) if row[3] else [],
                    "allowed_roles": allowed_roles,
                    "chunks": row[5],
                }
            )
        return documents

    def delete_document(self, document_id: int) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM knowledge_chunks WHERE document_id = ?",
                (document_id,),
            )
        return cursor.rowcount > 0
