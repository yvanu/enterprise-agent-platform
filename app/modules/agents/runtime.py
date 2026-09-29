from __future__ import annotations

from app.agents.data.agent import DataAgent
from app.agents.supervisor.agent import SupervisorAgent
from app.api.data import get_database, llm as shared_llm
from app.api.knowledge import agent as knowledge_agent
from app.api.ops import agent as ops_agent
from app.core.config import get_settings
from app.modules.agents.models import AgentDetail, AgentRunRequest, AgentRunResponse, AgentVersionView
from app.platform.auth import Identity
from app.platform.llm import OpenAICompatibleLLM
from app.platform.models import TraceStep
from app.platform.runs import start_run


def _published_version(agent: AgentDetail) -> AgentVersionView:
    if agent.status != "published" or agent.published_version is None:
        raise ValueError("Agent 尚未发布")
    version = next((item for item in agent.versions if item.version == agent.published_version), None)
    if version is None:
        raise RuntimeError("Published Version 不存在")
    return version


class AgentRuntime:
    def run(self, agent: AgentDetail, request: AgentRunRequest, identity: Identity) -> AgentRunResponse:
        version = _published_version(agent)
        run = start_run(
            agent.slug if agent.type == "generic" else agent.type,
            agent_id=agent.id,
            agent_version=version.version,
        )
        try:
            if agent.type == "data":
                answer = DataAgent(get_database(request.source), shared_llm).ask(request.input)
                run_id = run.success(answer.trace)
                return AgentRunResponse(
                    run_id=run_id,
                    agent_id=agent.id,
                    agent_version=version.version,
                    answer=answer.answer,
                    trace=[item.model_dump() for item in answer.trace],
                    raw=answer.model_dump(mode="json"),
                )

            if agent.type == "knowledge":
                answer = knowledge_agent.ask(request.input, role=identity.role)
                run_id = run.success(answer.trace)
                return AgentRunResponse(
                    run_id=run_id,
                    agent_id=agent.id,
                    agent_version=version.version,
                    answer=answer.answer,
                    trace=[item.model_dump() for item in answer.trace],
                    raw=answer.model_dump(mode="json"),
                )

            if agent.type == "ops":
                if identity.role not in {"operator", "admin"}:
                    raise PermissionError("Ops Agent 需要 operator/admin 权限")
                answer = ops_agent.diagnose(request.input)
                run_id = run.success(answer.trace)
                return AgentRunResponse(
                    run_id=run_id,
                    agent_id=agent.id,
                    agent_version=version.version,
                    answer=answer.answer,
                    trace=[item.model_dump() for item in answer.trace],
                    raw=answer.model_dump(mode="json"),
                )

            if agent.type == "supervisor":
                if identity.role not in {"operator", "admin"}:
                    raise PermissionError("Supervisor 需要 operator/admin 权限")
                supervisor = SupervisorAgent(
                    DataAgent(get_database(request.source), shared_llm),
                    knowledge_agent,
                    ops_agent,
                    shared_llm,
                )
                answer = supervisor.investigate(request.input, role=identity.role)
                run_id = run.success(answer.trace)
                return AgentRunResponse(
                    run_id=run_id,
                    agent_id=agent.id,
                    agent_version=version.version,
                    answer=answer.answer,
                    trace=[item.model_dump() for item in answer.trace],
                    raw=answer.model_dump(mode="json"),
                )

            llm = OpenAICompatibleLLM(get_settings())
            trace = [TraceStep(kind="llm", name="agent_response", detail=f"agent_version={version.version}")]
            messages = []
            if version.instructions.strip():
                messages.append({"role": "system", "content": version.instructions.strip()})
            messages.append({"role": "user", "content": request.input})
            answer = llm.chat(
                messages,
                model=version.model or None,
                temperature=version.temperature,
            )
            run_id = run.success(trace)
            return AgentRunResponse(
                run_id=run_id,
                agent_id=agent.id,
                agent_version=version.version,
                answer=answer,
                trace=[item.model_dump() for item in trace],
            )
        except Exception as exc:
            run.error(exc)
            raise


agent_runtime = AgentRuntime()
