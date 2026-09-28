import argparse
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.agents.data.agent import DataAgent
from app.agents.knowledge.agent import KnowledgeAgent
from app.agents.knowledge.store import KnowledgeStore
from app.agents.ops.agent import OpsAgent
from app.agents.supervisor.agent import SupervisorAgent
from app.agents.supervisor.models import IncidentAnswer
from app.core.config import Settings
from app.db.demo import initialize_demo_database
from app.db.engine import Database


QUESTION = "为什么最近导入任务失败？请结合当前运维状态、知识库手册和历史数据给出排查结论。"


class DemoLLM:
    def chat_json(self, messages: list[dict]) -> dict:
        prompt = messages[-1]["content"]
        if "查询结果：" in prompt:
            return {
                "answer": "历史导入记录中存在失败任务，失败记录需要结合当前超时日志继续排查。",
                "insights": ["导入任务并非全部失败，存在成功与失败两种状态。"],
            }
        return {
            "sql": (
                "SELECT status, COUNT(*) AS total, "
                "ROUND(AVG(duration_seconds), 1) AS avg_duration_seconds "
                "FROM import_jobs GROUP BY status ORDER BY status"
            ),
            "plan_summary": "统计导入任务成功/失败数量和平均耗时。",
        }

    def embed(self, texts: list[str]) -> list[list[float]]:
        vectors = []
        for text in texts:
            if any(word in text for word in ("导入", "超时", "上游", "依赖")):
                vectors.append([1.0, 0.0])
            else:
                vectors.append([0.0, 1.0])
        return vectors

    def chat(self, messages: list[dict]) -> str:
        system = messages[0]["content"]
        if "企业运维 Agent" in system:
            return "日志发现导入服务访问上游接口超时；当前应优先检查上游依赖与网络连通性。"
        if "企业知识 Agent" in system:
            return "运维手册规定：出现上游超时时，先检查依赖服务健康状态和网络，再考虑重试。[来源 1]"
        if "企业故障调查 Supervisor" in system:
            return (
                "综合结论：当前证据指向上游依赖超时。Ops 日志给出直接超时证据，"
                "Knowledge 手册给出标准排查顺序，Data 历史记录确认存在失败任务。"
                "建议先验证上游服务健康与网络，再决定是否重试；未执行任何修复动作。"
            )
        return "demo"


def run_demo(question: str = QUESTION) -> IncidentAnswer:
    with TemporaryDirectory() as directory:
        llm = DemoLLM()
        db = Database(
            Settings(
                database_url=f"sqlite:///{directory}/demo.db",
                agent_max_attempts=1,
            )
        )
        initialize_demo_database(db)

        knowledge = KnowledgeAgent(
            KnowledgeStore(f"{directory}/knowledge.db"),
            llm,
            top_k=2,
        )
        knowledge.add_document(
            "导入服务运维手册",
            "当导入服务出现上游请求超时时，先检查依赖服务健康状态、网络连通性和超时配置，再决定是否重试。",
            tags=["运维", "导入"],
            allowed_roles=["operator", "admin"],
        )
        knowledge.add_document(
            "数据验收规范",
            "雷达和海洋资料入库前需要检查完整性与时间范围。",
            tags=["验收"],
            allowed_roles=["operator", "admin"],
        )

        log_path = Path(directory) / "import-service.log"
        log_path.write_text(
            "INFO import job started\n"
            "ERROR upstream request timeout service=metadata-api timeout=5s\n",
            encoding="utf-8",
        )
        ops = OpsAgent(llm, log_files=str(log_path))
        supervisor = SupervisorAgent(
            DataAgent(db, llm),
            knowledge,
            ops,
            llm,
        )
        return supervisor.investigate(question, role="operator")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the offline multi-agent incident demo without external LLMs."
    )
    parser.add_argument("--question", default=QUESTION)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = run_demo(args.question)
    if args.json:
        print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))
        return 0

    print(f"QUESTION\n{result.question}\n")
    for finding in result.findings:
        print(f"[{finding.agent.upper()}] {finding.status}\n{finding.summary}\n")
    print(f"SUPERVISOR\n{result.answer}\n")
    print("TRACE")
    for step in result.trace:
        print(f"- {step.name}: {step.status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
