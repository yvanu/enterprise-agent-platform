from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

from app.api.data import db, router as data_router
from app.api.knowledge import router as knowledge_router
from app.api.ops import router as ops_router
from app.core.config import get_settings
from app.db.demo import initialize_demo_database


settings = get_settings()
initialize_demo_database(db)

app = FastAPI(title=settings.app_name)
app.include_router(data_router)
app.include_router(knowledge_router)
app.include_router(ops_router)


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(Path(__file__).parent / "static" / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
