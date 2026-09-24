import json
from typing import Any

from app.agents.data.models import AgentAnswer, ChartSpec, QueryResult, SqlAttempt
from app.db.engine import Database
from app.db.introspection import describe_schema, schema_to_prompt
from app.platform.llm import LLMResponseError, OpenAICompatibleLLM
from app.platform.models import TraceStep


def _chart(result: QueryResult) -> ChartSpec | None:
    if not result.rows or len(result.columns) < 2:
        return None

    x_column = result.columns[0]
    numeric = next(
        (
            column
            for column in result.columns[1:]
            if all(
                row.get(column) is None or isinstance(row.get(column), (int, float))
                for row in result.rows
            )
        ),
        None,
    )
    if not numeric:
        return None

    rows = [row for row in result.rows[:20] if isinstance(row.get(numeric), (int, float))]
    if not rows:
        return None
    return ChartSpec(
        title=f"{numeric} by {x_column}",
        labels=[str(row.get(x_column, "")) for row in rows],
        values=[float(row[numeric]) for row in rows],
        x_column=x_column,
        y_column=numeric,
    )


def _report(question: str, answer: str, insights: list[str], sql: str, result: QueryResult) -> str:
    lines = [f"# 数据分析报告", "", f"## 问题", question, "", "## 结论", answer]
    if insights:
        lines += ["", "## 关键发现", *[f"- {item}" for item in insights]]
    lines += ["", "## SQL", "```sql", sql, "```"]
    if result.rows:
        columns = result.columns
        lines += ["", "## 查询结果", "| " + " | ".join(columns) + " |", "| " + " | ".join(["---"] * len(columns)) + " |"]
        for row in result.rows[:20]:
            lines.append("| " + " | ".join(str(row.get(c, "")).replace("|", "\\|") for c in columns) + " |")
    return "\n".join(lines)


class DataAgent:
    def __init__(self, db: Database, llm: OpenAICompatibleLLM):
        self.db = db
        self.llm = llm

    def _generate_sql(
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

        data = self.llm.chat_json(
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
        sql = str(data.get("sql", "")).strip()
        if not sql:
            raise LLMResponseError("LLM 没有生成 SQL")
        return {"sql": sql, "plan_summary": str(data.get("plan_summary", "")).strip()}

    def _summarize(
        self,
        *,
        question: str,
        sql: str,
        result: dict[str, Any],
    ) -> dict[str, Any]:
        data = self.llm.chat_json(
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
        return {
            "answer": str(data.get("answer", "")).strip() or "查询完成。",
            "insights": [str(x) for x in data.get("insights", []) if str(x).strip()],
        }

    def ask(self, question: str) -> AgentAnswer:
        schema_info = describe_schema(self.db.engine, self.db.settings.database_schema)
        schema = schema_to_prompt(schema_info)
        trace = [TraceStep(kind="tool", name="schema", detail=f"{len(schema_info['tables'])} tables")]
        attempts: list[SqlAttempt] = []
        previous_error = None
        previous_sql = None

        for _ in range(self.db.settings.agent_max_attempts):
            generated = self._generate_sql(
                question=question,
                schema=schema,
                previous_error=previous_error,
                previous_sql=previous_sql,
            )
            sql = generated["sql"]
            trace.append(TraceStep(kind="llm", name="generate_sql", detail=generated["plan_summary"]))
            attempt = SqlAttempt(sql=sql, plan_summary=generated["plan_summary"])
            attempts.append(attempt)

            try:
                result = self.db.execute_readonly(sql)
            except Exception as exc:
                previous_sql = sql
                previous_error = str(exc)
                attempt.error = previous_error
                trace.append(TraceStep(kind="tool", name="database_query", status="error", detail=previous_error))
                continue

            trace.append(TraceStep(kind="tool", name="database_query", detail=f"{result.row_count} rows"))

            summary = self._summarize(
                question=question,
                sql=sql,
                result=result.model_dump(mode="json"),
            )
            trace.append(TraceStep(kind="llm", name="summarize"))
            chart = _chart(result)
            report = _report(question, summary["answer"], summary["insights"], sql, result)
            trace.append(TraceStep(kind="tool", name="presentation", detail="chart + markdown report"))
            return AgentAnswer(
                question=question,
                answer=summary["answer"],
                insights=summary["insights"],
                sql=sql,
                attempts=attempts,
                result=result,
                chart=chart,
                report_markdown=report,
                trace=trace,
            )

        raise RuntimeError(
            f"Agent 连续 {self.db.settings.agent_max_attempts} 次未能生成可执行 SQL："
            f"{previous_error or 'unknown error'}"
        )
