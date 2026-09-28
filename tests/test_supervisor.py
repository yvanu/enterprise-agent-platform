from types import SimpleNamespace

from app.agents.supervisor.agent import SupervisorAgent
from app.platform.models import TraceStep


class _Data:
    def ask(self, question: str):
        return SimpleNamespace(
            answer="历史数据中失败导入任务增加。",
            trace=[TraceStep(kind="tool", name="database_query")],
        )


class _Knowledge:
    def ask(self, question: str, *, role: str):
        assert role == "operator"
        return SimpleNamespace(
            answer="运维手册要求先检查上游依赖。",
            trace=[TraceStep(kind="tool", name="knowledge_search")],
        )


class _Ops:
    def diagnose(self, question: str):
        return SimpleNamespace(
            answer="当前日志出现连接超时。",
            trace=[TraceStep(kind="tool", name="system_snapshot")],
        )


class _LLM:
    def chat(self, messages):
        return "综合结论：优先排查上游依赖和连接超时。"


def test_supervisor_calls_three_agents_and_synthesizes():
    agent = SupervisorAgent(_Data(), _Knowledge(), _Ops(), _LLM())

    answer = agent.investigate("为什么导入服务失败？", role="operator")

    assert answer.answer.startswith("综合结论")
    assert [item.agent for item in answer.findings] == ["ops", "knowledge", "data"]
    assert [step.name for step in answer.trace] == [
        "delegate_ops",
        "delegate_knowledge",
        "delegate_data",
        "synthesize",
    ]


def test_supervisor_keeps_partial_results_when_one_agent_fails():
    class _BrokenKnowledge:
        def ask(self, question: str, *, role: str):
            raise RuntimeError("knowledge unavailable")

    agent = SupervisorAgent(_Data(), _BrokenKnowledge(), _Ops(), _LLM())

    answer = agent.investigate("为什么导入服务失败？", role="operator")

    knowledge = next(item for item in answer.findings if item.agent == "knowledge")
    assert knowledge.status == "error"
    assert answer.trace[1].status == "error"
    assert answer.trace[-1].name == "synthesize"
