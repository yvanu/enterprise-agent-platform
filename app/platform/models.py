from pydantic import BaseModel


class TraceStep(BaseModel):
    kind: str
    name: str
    status: str = "ok"
    detail: str = ""
