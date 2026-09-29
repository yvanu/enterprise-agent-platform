from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from app.core.config import get_settings
from app.modules.agents.base import Base


def build_engine(url: str) -> Engine:
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, future=True, pool_pre_ping=True, connect_args=connect_args)


settings = get_settings()
engine = build_engine(settings.platform_database_url)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)


def initialize_agent_store() -> None:
    from app.modules.agents import orm  # noqa: F401

    Base.metadata.create_all(engine)
