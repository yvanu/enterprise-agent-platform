import json
import logging
from contextvars import ContextVar
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException


request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)


class APIError(BaseModel):
    code: str
    message: str
    request_id: str | None = None
    correlation_id: str | None = None
    details: object | None = None


class APIErrorResponse(BaseModel):
    error: APIError


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "event": getattr(record, "event", record.getMessage()),
            **getattr(record, "fields", {}),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


logger = logging.getLogger("enterprise_agent")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(_JsonFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False


def log_event(event: str, **fields: object) -> None:
    logger.info(event, extra={"event": event, "fields": fields})


def current_request_context() -> tuple[str | None, str | None]:
    return request_id_var.get(), correlation_id_var.get()


def _correlation_id(request: Request) -> str:
    value = request.headers.get("x-correlation-id", "").strip()
    if value and len(value) <= 128 and all(c.isalnum() or c in "._-" for c in value):
        return value
    return uuid4().hex


def _error(
    *,
    code: str,
    message: str,
    status_code: int,
    details: object | None = None,
) -> JSONResponse:
    request_id, correlation_id = current_request_context()
    payload = APIErrorResponse(
        error=APIError(
            code=code,
            message=message,
            request_id=request_id,
            correlation_id=correlation_id,
            details=details,
        )
    )
    return JSONResponse(status_code=status_code, content=jsonable_encoder(payload))


def install_observability(app: FastAPI) -> None:
    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = uuid4().hex
        correlation_id = _correlation_id(request)
        request_token = request_id_var.set(request_id)
        correlation_token = correlation_id_var.set(correlation_id)
        started = perf_counter()
        error_type: str | None = None
        try:
            response = await call_next(request)
        except Exception as exc:
            error_type = type(exc).__name__
            logger.error(
                "http_request_error",
                extra={
                    "event": "http_request_error",
                    "fields": {
                        "request_id": request_id,
                        "correlation_id": correlation_id,
                        "method": request.method,
                        "path": request.url.path,
                        "error_type": error_type,
                    },
                },
                exc_info=True,
            )
            response = _error(
                code="INTERNAL_ERROR",
                message="服务器内部错误",
                status_code=500,
            )

        duration_ms = round((perf_counter() - started) * 1000)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Correlation-ID"] = correlation_id
        log_event(
            "http_request",
            request_id=request_id,
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
            error_type=error_type,
        )
        request_id_var.reset(request_token)
        correlation_id_var.reset(correlation_token)
        return response

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        detail = exc.detail
        message = detail if isinstance(detail, str) else "请求失败"
        return _error(
            code={
                401: "UNAUTHORIZED",
                403: "FORBIDDEN",
                404: "NOT_FOUND",
                409: "CONFLICT",
                413: "PAYLOAD_TOO_LARGE",
                503: "SERVICE_UNAVAILABLE",
            }.get(exc.status_code, "HTTP_ERROR"),
            message=message,
            status_code=exc.status_code,
            details=None if isinstance(detail, str) else detail,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ):
        return _error(
            code="VALIDATION_ERROR",
            message="请求参数校验失败",
            status_code=422,
            details=exc.errors(),
        )
