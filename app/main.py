from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app.api.agents import router as agents_router
from app.api.auth import router as auth_router
from app.api.data import db, router as data_router
from app.api.knowledge import agent as knowledge_agent, router as knowledge_router
from app.api.mcp import router as mcp_router
from app.api.ops import router as ops_router
from app.api.openapi import router as openapi_router
from app.api.platform import router as platform_router
from app.api.supervisor import router as supervisor_router
from app.api.tools import router as tools_router
from app.core.config import get_settings, validate_settings
from app.db.demo import initialize_demo_database
from app.modules.agents.service import agent_service
from app.modules.tools.service import tool_service
from app.platform.auth import current_identity
from app.platform.observability import install_observability
from app.platform.runs import run_store


settings = get_settings()
validate_settings(settings)
initialize_demo_database(db)
agent_service.initialize()
tool_service.initialize()

app = FastAPI(title=settings.app_name)
install_observability(app, rate_limit_per_minute=settings.rate_limit_per_minute)
app.include_router(auth_router)
for router in (agents_router, data_router, knowledge_router, ops_router, platform_router, supervisor_router, tools_router, mcp_router, openapi_router):
    app.include_router(router, dependencies=[Depends(current_identity)])

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.get("/login", include_in_schema=False)
def login_page() -> FileResponse:
    return FileResponse(static_dir / "login.html")


@app.get("/health")
@app.get("/health/live")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/ready")
def readiness() -> dict:
    checks: dict[str, str] = {}
    try:
        with db.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        checks["database"] = type(exc).__name__

    try:
        run_store.list(limit=1)
        checks["platform_store"] = "ok"
    except Exception as exc:
        checks["platform_store"] = type(exc).__name__

    try:
        knowledge_agent.store.list_documents()
        checks["knowledge_store"] = "ok"
    except Exception as exc:
        checks["knowledge_store"] = type(exc).__name__

    try:
        agent_service.list()
        checks["agent_store"] = "ok"
    except Exception as exc:
        checks["agent_store"] = type(exc).__name__

    try:
        tool_service.list(enabled_only=True)
        checks["tool_store"] = "ok"
    except Exception as exc:
        checks["tool_store"] = type(exc).__name__

    if any(value != "ok" for value in checks.values()):
        raise HTTPException(
            status_code=503,
            detail={"status": "not_ready", "checks": checks},
        )
    return {"status": "ready", "checks": checks}
