"""Deliberately narrow OpenAPI 3.x import for trusted enterprise JSON REST APIs.

The OpenAPI document is provided inline, never fetched. Only the operator's
exact allowlisted base URL is contacted. No $refs, auth, redirects or
operation-level server overrides in this first version.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.config import get_settings
from app.modules.agents.db import SessionLocal
from app.modules.agents.orm import AgentORM
from app.modules.tools.mcp_service import MCPInvocation
from app.modules.tools.orm import OpenAPIServiceORM, ToolORM
from app.platform.approvals import approval_store
from app.platform.policy import require_tool, tool_execution_context
from app.platform.runs import start_run
from app.platform.models import TraceStep

_OPERATION_ID = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,89}$")
_ENDPOINT = re.compile(r"^/(?!/)[a-zA-Z0-9_/{}/.-]*$")
_TEMPLATE = re.compile(r"{([a-zA-Z_][a-zA-Z0-9_]*)}")
_PATH_VALUE = re.compile(r"^[a-zA-Z0-9_-]{1,200}$")
_TYPES = {"string", "integer", "number", "boolean"}


class OpenAPIServiceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    base_url: str = Field(min_length=1, max_length=2048)
    document: dict


class OpenAPIServiceView(BaseModel):
    id: str
    name: str
    base_url: str
    operation_count: int
    created_at: datetime


def _validate_schema(schema: dict) -> dict:
    if not isinstance(schema, dict):
        raise ValueError("OpenAPI 参数 Schema 必须是对象")
    # Avoid unresolved remote or recursive schema references.
    def check(value):
        if isinstance(value, dict):
            if "$ref" in value:
                raise ValueError("此版本不支持 OpenAPI $ref，请先展开引用")
            for child in value.values():
                check(child)
        elif isinstance(value, list):
            for child in value:
                check(child)
    check(schema)
    return schema


def _parse_operations(document: dict) -> dict:
    if not isinstance(document, dict) or not str(document.get("openapi", "")).startswith("3."):
        raise ValueError("仅支持 OpenAPI 3.x JSON 文档")
    if len(json.dumps(document, ensure_ascii=False).encode()) > 262_144:
        raise ValueError("OpenAPI 文档超过 256KB")
    paths = document.get("paths")
    if not isinstance(paths, dict):
        raise ValueError("OpenAPI paths 必须是对象")
    result = {}
    for path, endpoint in paths.items():
        if (not isinstance(path, str) or not _ENDPOINT.fullmatch(path)
                or any(segment in {".", ".."} for segment in path.split("/"))
                or not isinstance(endpoint, dict)):
            raise ValueError("不支持的 OpenAPI 路径")
        if "{" in _TEMPLATE.sub("", path) or "}" in _TEMPLATE.sub("", path):
            raise ValueError("OpenAPI 路径变量语法无效")
        for method in ("get", "post"):
            operation = endpoint.get(method)
            if operation is None:
                continue
            if not isinstance(operation, dict):
                raise ValueError("OpenAPI Operation 必须是对象")
            op_id = operation.get("operationId")
            if not isinstance(op_id, str) or not _OPERATION_ID.fullmatch(op_id) or op_id in result:
                raise ValueError("OpenAPI operationId 必须唯一且为字母数字下划线")
            base_params, op_params = endpoint.get("parameters", []), operation.get("parameters", [])
            if not isinstance(base_params, list) or not isinstance(op_params, list):
                raise ValueError("OpenAPI parameters 必须是数组")
            params = base_params + op_params
            if not isinstance(params, list):
                raise ValueError("OpenAPI parameters 必须是数组")
            props, required = {}, []
            for location in ("path", "query"):
                fields, required_fields = {}, []
                for param in params:
                    if not isinstance(param, dict) or param.get("in") not in {"path", "query"}:
                        raise ValueError("此版本仅支持 path / query 参数")
                    if param["in"] != location:
                        continue
                    key = param.get("name")
                    schema = _validate_schema(param.get("schema", {}))
                    if (not isinstance(key, str) or not _OPERATION_ID.fullmatch(key)
                            or schema.get("type") not in _TYPES or key in fields):
                        raise ValueError("OpenAPI 参数必须唯一且为简单标量")
                    fields[key] = {"type": schema["type"]}
                    if param.get("required", False) or location == "path":
                        required_fields.append(key)
                if fields:
                    props[location] = {"type": "object", "properties": fields,
                                       "required": required_fields, "additionalProperties": False}
                    if required_fields:
                        required.append(location)
            path_names = set(_TEMPLATE.findall(path))
            if path_names != set(props.get("path", {}).get("properties", {})):
                raise ValueError("OpenAPI 路径变量与 path 参数定义不匹配")
            body_schema = None
            body = operation.get("requestBody")
            if body is not None:
                if method != "post" or not isinstance(body, dict):
                    raise ValueError("GET 不支持请求体")
                media = body.get("content", {}).get("application/json", {})
                body_schema = _validate_schema(media.get("schema", {}))
                if body_schema.get("type") != "object":
                    raise ValueError("只支持 JSON 对象请求体")
                props["body"] = body_schema
                if body.get("required", False):
                    required.append("body")
            if method == "post" and body is None:
                # Empty-body POST is supported.
                pass
            schema = {"type": "object", "properties": props,
                      "required": required, "additionalProperties": False}
            result[op_id] = {
                "method": method.upper(), "path": path, "schema": schema,
                "description": str(operation.get("summary") or operation.get("description") or op_id)[:2000],
            }
            if len(result) > 30:
                raise ValueError("单次最多导入 30 个 OpenAPI Operation")
    if not result:
        raise ValueError("未找到支持的 GET/POST Operation")
    return result


def _validate_arguments(operation: dict, arguments: dict) -> tuple[str, dict, dict | None]:
    schema = operation["schema"]
    if not isinstance(arguments, dict) or set(arguments) - set(schema["properties"]):
        raise ValueError("OpenAPI 操作参数包含未知字段")
    values = {}
    for section, section_schema in schema["properties"].items():
        value = arguments.get(section)
        if value is None:
            if section in schema.get("required", []):
                raise ValueError(f"缺少必要参数: {section}")
            continue
        if not isinstance(value, dict):
            raise ValueError(f"{section} 必须是 JSON object")
        if section != "body":
            types = section_schema["properties"]
            if set(value) - set(types) or set(section_schema.get("required", [])) - set(value):
                raise ValueError(f"{section} 参数名称或必填字段错误")
            for key, param in value.items():
                kind = types[key]["type"]
                valid = (
                    type(param) is str if kind == "string" else
                    type(param) is int if kind == "integer" else
                    type(param) in (int, float) if kind == "number" else
                    type(param) is bool
                )
                if not valid:
                    raise ValueError(f"{section}.{key} 类型错误")
                if section == "path" and not _PATH_VALUE.fullmatch(str(param)):
                    raise ValueError("路径变量不允许包含斜杠或特殊字符")
        values[section] = value
    path = operation["path"]
    for key, value in values.get("path", {}).items():
        path = path.replace("{" + key + "}", str(value))
    query = values.get("query", {})
    body = values.get("body")
    return path, query, body


class OpenAPIService:
    @staticmethod
    def _check_url(url: str) -> None:
        allowed = {item.strip() for item in get_settings().openapi_allowed_base_urls.split(",") if item.strip()}
        p = urlsplit(url)
        if (url not in allowed or p.scheme not in {"https", "http"} or not p.hostname
                or p.username or p.password or p.query or p.fragment or not p.netloc
                or (p.path and (".." in p.path.split("/") or "//" in p.path))
                or (get_settings().app_env.lower() in {"prod", "production"} and p.scheme != "https")):
            raise ValueError("OpenAPI base_url 必须预先加入 OPENAPI_ALLOWED_BASE_URLS；生产环境必须 HTTPS")

    def _client(self, timeout: int) -> httpx.Client:
        return httpx.Client(timeout=timeout, follow_redirects=False, trust_env=False)

    def register(self, request: OpenAPIServiceCreate) -> OpenAPIServiceView:
        self._check_url(request.base_url)
        operations = _parse_operations(request.document)
        with SessionLocal() as session:
            service = OpenAPIServiceORM(
                id=str(uuid4()), name=request.name, base_url=request.base_url,
                operations=operations,
            )
            session.add(service)
            session.flush()
            for name, operation in operations.items():
                namespace = f"openapi.{service.id}"
                session.add(ToolORM(
                    id=str(uuid4()), key=f"{namespace}.{name}",
                    namespace=namespace, name=name, display_name=name,
                    description=operation["description"], provider="openapi",
                    type="http", mode="write", risk="high", approval_required=True,
                    input_schema=operation["schema"], output_schema={},
                    timeout_seconds=15, enabled=True,
                ))
            session.commit()
            session.refresh(service)
            return OpenAPIServiceView(
                id=service.id, name=service.name, base_url=service.base_url,
                operation_count=len(operations), created_at=service.created_at)

    def list(self) -> list[OpenAPIServiceView]:
        with SessionLocal() as session:
            rows = session.scalars(select(OpenAPIServiceORM).order_by(OpenAPIServiceORM.created_at))
            return [OpenAPIServiceView(
                id=row.id, name=row.name, base_url=row.base_url,
                operation_count=len(row.operations), created_at=row.created_at
            ) for row in rows]

    def call_assigned(self, agent_id: str, agent_version: int, tool_id: str,
                      request: MCPInvocation, *, actor: str) -> dict:
        with SessionLocal() as session:
            agent = session.get(AgentORM, agent_id)
            if agent is None or agent.status != "published" or agent.published_version != agent_version:
                raise ValueError("Agent Version 不是当前发布版本")
            tool = session.get(ToolORM, tool_id)
            if tool is None or tool.provider != "openapi" or not tool.enabled:
                raise KeyError("OpenAPI Tool 不存在或已禁用")
            service = session.get(OpenAPIServiceORM, tool.namespace.removeprefix("openapi."))
            if service is None or tool.name not in service.operations:
                raise ValueError("OpenAPI service 不存在")
            self._check_url(service.base_url)
            operation = service.operations[tool.name]
            path, params, body = _validate_arguments(operation, request.arguments)
            url = service.base_url.rstrip("/") + path
            namespace, name, mode, timeout = tool.namespace, tool.name, tool.mode, tool.timeout_seconds

        with tool_execution_context(agent_id, agent_version):
            require_tool(namespace, name, mode, approval_granted=bool(request.approval_id))
            if request.approval_id is None:
                raise PermissionError("OpenAPI 调用需要参数级人工审批")
            approval_store.consume(
                request.approval_id, agent=namespace, tool=name, target=f"tool:{tool_id}",
                actor=actor, arguments=request.arguments, agent_id=agent_id, agent_version=agent_version,
            )
            with self._client(timeout) as client:
                with client.stream(operation["method"], url, params=params,
                                   json=body if body is not None else None) as response:
                    if response.status_code >= 300:
                        raise httpx.HTTPStatusError(
                            f"OpenAPI HTTP error {response.status_code}", request=response.request, response=response)
                    result = bytearray()
                    for chunk in response.iter_bytes():
                        result.extend(chunk)
                        if len(result) > 1_048_576:
                            raise ValueError("OpenAPI 响应超过 1MB")
                    text = result.decode("utf-8", errors="replace")
                    try:
                        data = json.loads(text)
                    except json.JSONDecodeError:
                        data = text
                    return {"status_code": response.status_code, "data": data}

    def invoke(self, agent_id: str, tool_id: str, request: MCPInvocation, *, actor: str) -> dict:
        with SessionLocal() as session:
            agent = session.get(AgentORM, agent_id)
            if agent is None or agent.published_version is None or agent.status != "published":
                raise ValueError("Agent 尚未发布")
            tool = session.get(ToolORM, tool_id)
            version, slug, name = agent.published_version, agent.slug, tool.key if tool else tool_id
        run = start_run(slug, agent_id=agent_id, agent_version=version)
        try:
            result = self.call_assigned(agent_id, version, tool_id, request, actor=actor)
            run_id = run.success([TraceStep(kind="tool", name=name, detail="approved OpenAPI call")])
            return {"run_id": run_id, "result": result}
        except Exception as exc:
            run.error(exc)
            raise


openapi_service = OpenAPIService()
