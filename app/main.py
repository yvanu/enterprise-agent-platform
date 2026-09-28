from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse

from app.api.auth import router as auth_router
from app.api.data import db, router as data_router
from app.api.knowledge import router as knowledge_router
from app.api.ops import router as ops_router
from app.api.platform import router as platform_router
from app.api.supervisor import router as supervisor_router
from app.core.config import get_settings
from app.db.demo import initialize_demo_database
from app.platform.auth import current_identity
from app.platform.observability import install_observability


settings = get_settings()
initialize_demo_database(db)

app = FastAPI(title=settings.app_name)
install_observability(app)
app.include_router(auth_router)
for router in (data_router, knowledge_router, ops_router, platform_router, supervisor_router):
    app.include_router(router, dependencies=[Depends(current_identity)])


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
