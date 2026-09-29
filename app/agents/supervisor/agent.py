import json

from app.agents.data.agent import DataAgent
from app.agents.knowledge.agent import KnowledgeAgent
from app.agents.ops.agent import OpsAgent
from app.agents.supervisor.models import AgentFinding, IncidentAnswer
from app.platform.llm import OpenAICompatibleLLM
from app.platform.models import TraceStep
from app.platform.policy import builtin_tool_execution_context


class SupervisorAgent:
    def __init__(
        self,
        data_agent: DataAgent,
        knowledge_agent: KnowledgeAgent,
        ops_agent: OpsAgent,
        llm: OpenAICompatibleLLM,
    ):
        self.data_agent = data_agent
        self.knowledge_agent = knowledge_agent
        self.ops_agent = ops_agent
        self.llm = llm

    def investigate(self, question: str, *, role: str) -> IncidentAnswer:
        findings: list[AgentFinding] = []
        trace: list[TraceStep] = []

        def delegated(agent_type: str, call):
            with builtin_tool_execution_context(agent_type):
                return call()

        delegates = [
            ("ops", lambda: delegated("ops", lambda: self.ops_agent.diagnose(question))),
            ("knowledge", lambda: delegated("knowledge", lambda: self.knowledge_agent.ask(question, role=role))),
            ("data", lambda: delegated("data", lambda: self.data_agent.ask(question))),
        ]
        for name, call in delegates:
            try:
                answer = call()
                findings.append(
                    AgentFinding(
                        agent=name,
                        status="ok",
                        summary=answer.answer,
                        trace=answer.trace,
                    )
                )
                trace.append(TraceStep(kind="agent", name=f"delegate_{name}"))
            except Exception as exc:
                findings.append(
                    AgentFinding(
                        agent=name,
                        status="error",
                        summary=f"{type(exc).__name__}: {exc}",
                    )
                )
                trace.append(
                    TraceStep(
                        kind="agent",
                        name=f"delegate_{name}",
                        status="error",
                        detail=type(exc).__name__,
                    )
                )

        successful = [item for item in findings if item.status == "ok"]
        if not successful:
            raise RuntimeError("所有子 Agent 都执行失败")

        context = {
            item.agent: item.summary
            for item in successful
        }
        answer = self.llm.chat(
            [
                {
                    "role": "system",
                    "content": (
                        "你是企业故障调查 Supervisor。综合 Ops、Knowledge、Data 三个 Agent "
                        "提供的只读证据形成结论。必须区分事实、推断和待验证项；"
                        "不得声称已执行修复动作。"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"问题：{question}\n\n"
                        f"子 Agent 证据：{json.dumps(context, ensure_ascii=False)}"
                    ),
                },
            ]
        )
        trace.append(TraceStep(kind="llm", name="synthesize"))
        return IncidentAnswer(
            question=question,
            answer=answer,
            findings=findings,
            trace=trace,
        )
