import json
import re
from typing import Any

import httpx

from app.core.config import Settings


class LLMNotConfiguredError(RuntimeError):
    pass


class LLMResponseError(RuntimeError):
    pass


_JSON_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL | re.IGNORECASE)


class OpenAICompatibleLLM:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _headers(self) -> dict[str, str]:
        return (
            {"Authorization": f"Bearer {self.settings.llm_api_key}"}
            if self.settings.llm_api_key
            else {}
        )

    def chat(self, messages: list[dict[str, str]]) -> str:
        if not self.settings.llm_model:
            raise LLMNotConfiguredError("请配置 LLM_MODEL")

        with httpx.Client(
            base_url=self.settings.llm_base_url.rstrip("/") + "/",
            timeout=self.settings.llm_timeout_seconds,
        ) as client:
            response = client.post(
                "chat/completions",
                headers=self._headers(),
                json={
                    "model": self.settings.llm_model,
                    "messages": messages,
                    "temperature": 0,
                },
            )
            response.raise_for_status()

        try:
            return response.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMResponseError("LLM 返回格式不符合 OpenAI Chat Completions 规范") from exc

    def chat_json(self, messages: list[dict[str, str]]) -> dict[str, Any]:
        content = self.chat(messages)
        match = _JSON_FENCE.match(content)
        if match:
            content = match.group(1)

        try:
            value = json.loads(content)
        except json.JSONDecodeError:
            start, end = content.find("{"), content.rfind("}")
            if start < 0 or end <= start:
                raise LLMResponseError("LLM 未返回 JSON")
            try:
                value = json.loads(content[start : end + 1])
            except json.JSONDecodeError as exc:
                raise LLMResponseError("LLM 返回的 JSON 无法解析") from exc

        if not isinstance(value, dict):
            raise LLMResponseError("LLM 返回值必须是 JSON object")
        return value

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.settings.embedding_model:
            raise LLMNotConfiguredError("请配置 EMBEDDING_MODEL")
        with httpx.Client(
            base_url=self.settings.llm_base_url.rstrip("/") + "/",
            timeout=self.settings.llm_timeout_seconds,
        ) as client:
            response = client.post(
                "embeddings",
                headers=self._headers(),
                json={"model": self.settings.embedding_model, "input": texts},
            )
            response.raise_for_status()
        try:
            return [item["embedding"] for item in response.json()["data"]]
        except (KeyError, TypeError) as exc:
            raise LLMResponseError("Embedding 返回格式不正确") from exc
