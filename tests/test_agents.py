from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.modules.agents import runtime as runtime_module
from app.modules.agents import service as service_module
from app.modules.agents.base import Base
from app.modules.agents.service import agent_service
from app.platform import auth as auth_module
from app.platform.runs import run_store


class _FakeLLM:
    def __init__(self, settings):
        self.settings = settings

    def chat(self, messages, *, model=None, temperature=0):
        assert messages[-1]["content"] == "hello"
        return "hello from custom agent"


def test_built_in_agents_seeded():
    agents = agent_service.list()
    built_ins = {item.type for item in agents if item.built_in}

    assert {"data", "knowledge", "ops", "supervisor"}.issubset(built_ins)
    assert all(item.status == "published" for item in agents if item.built_in)
    assert all(item.published_version == 1 for item in agents if item.built_in)


def test_custom_agent_lifecycle_and_run(monkeypatch, tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'agents.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    monkeypatch.setattr(service_module, "SessionLocal", session_factory)
    agent_service.seed_built_ins()

    monkeypatch.setattr(auth_module.settings, "auth_enabled", False)
    monkeypatch.setattr(runtime_module, "OpenAICompatibleLLM", _FakeLLM)
    client = TestClient(app)

    created = client.post(
        "/api/v1/agents",
        json={
            "name": "Interview Test Agent",
            "description": "Custom M1 lifecycle test",
            "type": "generic",
            "version": {
                "instructions": "Answer briefly.",
                "model": "test-model",
                "temperature": 0.1,
            },
        },
    )
    assert created.status_code == 201
    agent = created.json()
    agent_id = agent["id"]
    assert agent["status"] == "draft"
    assert agent["latest_version"] == 1
    assert agent["published_version"] is None

    blocked = client.post(
        f"/api/v1/agents/{agent_id}/run",
        json={"input": "hello"},
    )
    assert blocked.status_code == 409

    published = client.post(f"/api/v1/agents/{agent_id}/publish", json={"version": 1})
    assert published.status_code == 200
    assert published.json()["status"] == "published"
    assert published.json()["published_version"] == 1

    run = client.post(
        f"/api/v1/agents/{agent_id}/run",
        json={"input": "hello"},
    )
    assert run.status_code == 200
    payload = run.json()
    assert payload["answer"] == "hello from custom agent"
    assert payload["agent_id"] == agent_id
    assert payload["agent_version"] == 1
    assert payload["run_id"]

    recorded = run_store.get(payload["run_id"])
    assert recorded is not None
    assert recorded.agent_id == agent_id
    assert recorded.agent_version == 1

    new_version = client.post(
        f"/api/v1/agents/{agent_id}/versions",
        json={"instructions": "Version two.", "temperature": 0.3},
    )
    assert new_version.status_code == 201
    assert new_version.json()["version"] == 2
    assert new_version.json()["status"] == "draft"

    versions_response = client.get(f"/api/v1/agents/{agent_id}/versions")
    assert versions_response.status_code == 200
    assert [item["version"] for item in versions_response.json()] == [2, 1]

    republished = client.post(f"/api/v1/agents/{agent_id}/publish", json={"version": 2})
    assert republished.status_code == 200
    versions = republished.json()["versions"]
    assert republished.json()["published_version"] == 2
    assert {item["version"]: item["status"] for item in versions}[1] == "archived"
    assert {item["version"]: item["status"] for item in versions}[2] == "published"

    rollback = client.post(f"/api/v1/agents/{agent_id}/publish", json={"version": 1})
    assert rollback.status_code == 200
    assert rollback.json()["published_version"] == 1

    archived = client.post(f"/api/v1/agents/{agent_id}/archive", json={})
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"
