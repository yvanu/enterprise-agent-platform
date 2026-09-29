import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.modules.agents import service as agent_service_module
from app.modules.agents.base import Base
from app.modules.agents.models import AgentCreate, AgentVersionPatch
from app.modules.agents.service import agent_service
from app.modules.tools import service as tool_service_module
from app.modules.tools.service import tool_service
from app.platform import auth as auth_module
from app.platform.policy import ToolPolicyError, require_tool, tool_execution_context


@pytest.fixture()
def isolated_tool_store(monkeypatch, tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'tools.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    monkeypatch.setattr(agent_service_module, "SessionLocal", factory)
    monkeypatch.setattr(tool_service_module, "SessionLocal", factory)

    agent_service.seed_built_ins()
    tool_service.seed_builtin_tools()
    tool_service.seed_builtin_assignments()
    return factory


def test_tool_registry_and_builtin_assignments(isolated_tool_store):
    tools = tool_service.list()
    assert any(item.key == "data.readonly_sql" and item.mode == "read" for item in tools)
    assert any(item.key == "ops.service_restart" and item.approval_required for item in tools)

    data_agent = next(item for item in agent_service.list() if item.type == "data")
    assigned = tool_service.list_version_tools(data_agent.id, 1)
    assert {item.tool.key for item in assigned} == {
        "data.schema",
        "data.readonly_sql",
        "data.report",
    }


def test_agent_tool_assignment_is_versioned_and_enforced(isolated_tool_store):
    agent = agent_service.create(AgentCreate(name="Tool Test Agent"), actor="tester")
    registry = {item.key: item for item in tool_service.list()}
    selected = [registry["data.schema"].id, registry["ops.snapshot"].id]

    assigned = tool_service.replace_version_tools(agent.id, 1, selected)
    assert {item.tool.key for item in assigned} == {"data.schema", "ops.snapshot"}

    with tool_execution_context(agent.id, 1):
        assert require_tool("data", "schema", "read").key == "data.schema"
        with pytest.raises(ToolPolicyError, match="未分配"):
            require_tool("data", "readonly_sql", "read")

    agent_service.publish(agent.id, 1)
    with pytest.raises(ValueError, match="Draft"):
        tool_service.replace_version_tools(agent.id, 1, [registry["data.report"].id])

    created = agent_service.create_version(
        agent.id,
        AgentVersionPatch(instructions="v2"),
        actor="tester",
    )
    assert created.version == 2
    cloned = tool_service.list_version_tools(agent.id, 2)
    assert {item.tool.key for item in cloned} == {"data.schema", "ops.snapshot"}


def test_builtin_workspace_enforces_published_tool_assignment(
    isolated_tool_store,
    monkeypatch,
):
    from app.main import app

    monkeypatch.setattr(auth_module.settings, "auth_enabled", False)
    data_agent = next(item for item in agent_service.list() if item.type == "data")
    registry = {item.key: item for item in tool_service.list()}

    with isolated_tool_store() as session:
        tool_service._replace_in_session(
            session,
            data_agent.id,
            1,
            [registry["data.report"].id],
            allow_published=True,
        )

    response = TestClient(app).get("/api/v1/data/schema")
    assert response.status_code == 400
    assert "未分配 Tool: data.schema" in str(response.json())
