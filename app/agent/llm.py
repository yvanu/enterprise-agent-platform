import json
import re
from typing import Any

import httpx

from app.core.config import Settings


class LLMNotConfiguredError(RuntimeError):
    pass


class LLMResponseError(RuntimeError):
    pass


_JSON_FENCE = re.compile(r"^\s*\`\`\`(?:json)?\s*(.*?)\s*\`\`\`\s*$", re.DOTALL | re.IGNORECASE)


class OpenAICompatibleLLM:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _chat(self, messages: list[dict[str, str]]) -> str:
        if not self.settings.llm_model:
            raise LLMNotConfiguredError("请配置 LLM_MODEL")

        headers = (
            {"Authorization": f"Bearer {self.settings.llm_api_key}"}
            if self.settings.llm_api_key
            else {}
        )
        with httpx.Client(
            base_url=self.settings.llm_base_url.rstrip("/") + "/",
            timeout=self.settings.llm_timeout_seconds,
        ) as client:
            response = client.post(
                "chat/completions",
                headers=headers,
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

    @staticmethod
    def _json(content: str) -> dict[str, Any]:
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

    def generate_sql(
        self,
        *,
        question: str,
        schema: str,
        previous_error: str | None = None,
        previous_sql: str | None = None,
    ) -> dict[str, str]:
        retry = ""
        if previous_error:
            retry = (
                f"\n上一次 SQL：{previous_sql}\n"
                f"数据库/安全网关错误：{previous_error}\n"
                "请分析错误并修正 SQL。"
            )

        content = self._chat(
            [
                {
                    "role": "system",
                    "content": (
                        "你是企业数据分析 Agent。只生成只读 SELECT/CTE SQL。"
                        "禁止写操作、DDL、文件函数、系统管理函数。"
                        "只能使用给定 Schema 中真实存在的表和字段。"
                        "返回纯 JSON："
                        '{"sql":"...","plan_summary":"一句话说明查询思路"}。'
                    ),
                },
                {
                    "role": "user",
                    "content": f"Schema:\n{schema}\n\n问题：{question}{retry}",
                },
            ]
        )
        data = self._json(content)
        sql = str(data.get("sql", "")).strip()
        if not sql:
            raise LLMResponseError("LLM 没有生成 SQL")
        return {"sql": sql, "plan_summary": str(data.get("plan_summary", "")).strip()}

    def summarize(self, *, question: str, sql: str, result: dict[str, Any]) -> dict[str, Any]:
        content = self._chat(
            [
                {
                    "role": "system",
                    "content": (
                        "你是企业数据分析师。根据查询结果回答问题，不得编造结果中不存在的数据。"
                        "返回纯 JSON："
                        '{"answer":"简洁结论","insights":["关键发现1","关键发现2"]}。'
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"问题：{question}\nSQL：{sql}\n"
                        f"查询结果：{json.dumps(result, ensure_ascii=False, default=str)}"
                    ),
                },
            ]
        )
        data = self._json(content)
        return {
            "answer": str(data.get("answer", "")).strip() or "查询完成。",
            "insights": [str(x) for x in data.get("insights", []) if str(x).strip()],
        }
