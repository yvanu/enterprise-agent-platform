from tempfile import TemporaryDirectory

from pydantic import BaseModel

from app.agents.data.agent import DataAgent
from app.agents.knowledge.agent import KnowledgeAgent
from app.agents.knowledge.store import KnowledgeStore
from app.core.config import Settings
from app.db.demo import initialize_demo_database
from app.db.engine import Database


class RegressionCaseResult(BaseModel):
    id: str
    agent: str
    passed: bool
    detail: str


class RegressionReport(BaseModel):
    mode: str = "offline"
    passed: bool
    passed_cases: int
    total_cases: int
    cases: list[RegressionCaseResult]


class _DataLLM:
    def chat_json(self, messages: list[dict]) -> dict:
        prompt = messages[-1]["content"]
        if "查询结果：" in prompt:
            return {"answer": "回归检查完成。", "insights": []}
        if "失败导入" in prompt:
            return {
                "sql": "SELECT COUNT(*) AS total FROM import_jobs WHERE status = 'failed'",
                "plan_summary": "统计失败导入任务。",
            }
        return {
            "sql": (
                "SELECT main_type, COUNT(*) AS total "
                "FROM data_assets GROUP BY main_type "
                "ORDER BY total DESC, main_type"
            ),
            "plan_summary": "按数据分类统计数量。",
        }


class _KnowledgeLLM:
    def embed(self, texts: list[str]) -> list[list[float]]:
        return [
            [1.0, 0.0] if "雷达" in text else [0.0, 1.0]
            for text in texts
        ]

    def chat(self, messages: list[dict]) -> str:
        return "根据命中的知识来源回答。[来源 1]"


def _result(case_id: str, agent: str, passed: bool, detail: str) -> RegressionCaseResult:
    return RegressionCaseResult(
        id=case_id,
        agent=agent,
        passed=passed,
        detail=detail,
    )


def run_regression_suite() -> RegressionReport:
    cases: list[RegressionCaseResult] = []

    with TemporaryDirectory() as directory:
        db = Database(
            Settings(
                database_url=f"sqlite:///{directory}/demo.db",
                agent_max_attempts=1,
            )
        )
        initialize_demo_database(db)
        data_agent = DataAgent(db, _DataLLM())

        try:
            answer = data_agent.ask("统计每类数据数量")
            totals = {row["main_type"]: row["total"] for row in answer.result.rows}
            passed = totals.get("海洋环境") == 3 and answer.result.row_count == 4
            cases.append(
                _result(
                    "data-category-counts",
                    "data",
                    passed,
                    f"海洋环境={totals.get('海洋环境')}, categories={answer.result.row_count}",
                )
            )
        except Exception as exc:
            cases.append(_result("data-category-counts", "data", False, type(exc).__name__))

        try:
            answer = data_agent.ask("统计失败导入任务数量")
            total = answer.result.rows[0]["total"]
            cases.append(
                _result(
                    "data-failed-imports",
                    "data",
                    total == 1,
                    f"failed={total}",
                )
            )
        except Exception as exc:
            cases.append(_result("data-failed-imports", "data", False, type(exc).__name__))

        store = KnowledgeStore(f"{directory}/knowledge.db")
        knowledge_agent = KnowledgeAgent(store, _KnowledgeLLM(), top_k=1)
        knowledge_agent.add_document("雷达验收规范", "雷达资料验收需要检查完整性。")
        knowledge_agent.add_document("海洋数据规范", "海温与盐度数据需要校验时间范围。")

        for case_id, question, expected_title in [
            ("knowledge-radar-retrieval", "雷达资料如何验收？", "雷达验收规范"),
            ("knowledge-ocean-retrieval", "海温数据检查什么？", "海洋数据规范"),
        ]:
            try:
                answer = knowledge_agent.ask(question)
                actual = answer.sources[0].title if answer.sources else ""
                cases.append(
                    _result(
                        case_id,
                        "knowledge",
                        actual == expected_title,
                        f"source={actual or 'none'}",
                    )
                )
            except Exception as exc:
                cases.append(_result(case_id, "knowledge", False, type(exc).__name__))

    passed_cases = sum(case.passed for case in cases)
    return RegressionReport(
        passed=passed_cases == len(cases),
        passed_cases=passed_cases,
        total_cases=len(cases),
        cases=cases,
    )
