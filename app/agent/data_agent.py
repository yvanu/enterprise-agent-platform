from app.agent.llm import OpenAICompatibleLLM
from app.agent.models import AgentAnswer, SqlAttempt
from app.db.engine import Database
from app.db.introspection import describe_schema, schema_to_prompt


class DataAgent:
    def __init__(self, db: Database, llm: OpenAICompatibleLLM):
        self.db = db
        self.llm = llm

    def ask(self, question: str) -> AgentAnswer:
        schema = schema_to_prompt(
            describe_schema(self.db.engine, self.db.settings.database_schema)
        )
        attempts: list[SqlAttempt] = []
        previous_error = None
        previous_sql = None

        for _ in range(self.db.settings.agent_max_attempts):
            generated = self.llm.generate_sql(
                question=question,
                schema=schema,
                previous_error=previous_error,
                previous_sql=previous_sql,
            )
            sql = generated["sql"]
            attempt = SqlAttempt(sql=sql, plan_summary=generated["plan_summary"])
            attempts.append(attempt)

            try:
                result = self.db.execute_readonly(sql)
            except Exception as exc:
                previous_sql = sql
                previous_error = str(exc)
                attempt.error = previous_error
                continue

            summary = self.llm.summarize(
                question=question,
                sql=sql,
                result=result.model_dump(mode="json"),
            )
            return AgentAnswer(
                question=question,
                answer=summary["answer"],
                insights=summary["insights"],
                sql=sql,
                attempts=attempts,
                result=result,
            )

        raise RuntimeError(
            f"Agent 连续 {self.db.settings.agent_max_attempts} 次未能生成可执行 SQL："
            f"{previous_error or 'unknown error'}"
        )
