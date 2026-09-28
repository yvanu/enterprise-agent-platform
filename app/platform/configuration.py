import json
import os
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, SecretStr

from app.core.config import DataSourceConfig, Settings


class PlatformSettingsUpdate(BaseModel):
    llm_base_url: str | None = Field(default=None, max_length=2000)
    llm_api_key: str | None = Field(default=None, max_length=10000)
    clear_llm_api_key: bool = False
    llm_model: str | None = Field(default=None, max_length=500)
    embedding_model: str | None = Field(default=None, max_length=500)
    llm_timeout_seconds: int | None = Field(default=None, ge=1, le=600)
    agent_max_attempts: int | None = Field(default=None, ge=1, le=10)

    database_url: str | None = Field(default=None, max_length=4000)
    database_schema: str | None = Field(default=None, max_length=500)
    data_sources: dict[str, DataSourceConfig] | None = None
    sql_max_rows: int | None = Field(default=None, ge=1, le=10000)
    sql_timeout_seconds: int | None = Field(default=None, ge=1, le=600)

    knowledge_top_k: int | None = Field(default=None, ge=1, le=100)
    knowledge_max_upload_bytes: int | None = Field(default=None, ge=1024, le=1024 * 1024 * 1024)

    ops_log_files: str | None = Field(default=None, max_length=10000)
    prometheus_url: str | None = Field(default=None, max_length=2000)
    ops_http_timeout_seconds: int | None = Field(default=None, ge=1, le=600)
    ops_enable_docker: bool | None = None
    ops_enable_kubernetes: bool | None = None
    ops_allowed_services: str | None = Field(default=None, max_length=5000)
    ops_command_timeout_seconds: int | None = Field(default=None, ge=1, le=600)

    rate_limit_per_minute: int | None = Field(default=None, ge=0, le=100000)


class SettingsTestRequest(BaseModel):
    target: Literal["chat", "embedding"]


CONFIGURABLE_FIELDS = {
    "llm_base_url",
    "llm_api_key",
    "llm_model",
    "embedding_model",
    "llm_timeout_seconds",
    "agent_max_attempts",
    "database_url",
    "database_schema",
    "data_sources",
    "sql_max_rows",
    "sql_timeout_seconds",
    "knowledge_top_k",
    "knowledge_max_upload_bytes",
    "ops_log_files",
    "prometheus_url",
    "ops_http_timeout_seconds",
    "ops_enable_docker",
    "ops_enable_kubernetes",
    "ops_allowed_services",
    "ops_command_timeout_seconds",
    "rate_limit_per_minute",
}

RESTART_REQUIRED_FIELDS = {
    "database_url",
    "database_schema",
    "rate_limit_per_minute",
}


def settings_view(settings: Settings) -> dict:
    return {
        "app_name": settings.app_name,
        "app_env": settings.app_env,
        "auth_enabled": settings.auth_enabled,
        "llm_base_url": settings.llm_base_url,
        "llm_api_key_configured": bool(settings.llm_api_key.get_secret_value()),
        "llm_model": settings.llm_model,
        "embedding_model": settings.embedding_model,
        "llm_timeout_seconds": settings.llm_timeout_seconds,
        "agent_max_attempts": settings.agent_max_attempts,
        "database_url": settings.database_url,
        "database_schema": settings.database_schema,
        "data_sources": {
            name: config.model_dump(by_alias=True)
            for name, config in settings.data_sources.items()
        },
        "sql_max_rows": settings.sql_max_rows,
        "sql_timeout_seconds": settings.sql_timeout_seconds,
        "knowledge_top_k": settings.knowledge_top_k,
        "knowledge_max_upload_bytes": settings.knowledge_max_upload_bytes,
        "ops_log_files": settings.ops_log_files,
        "prometheus_url": settings.prometheus_url,
        "ops_http_timeout_seconds": settings.ops_http_timeout_seconds,
        "ops_enable_docker": settings.ops_enable_docker,
        "ops_enable_kubernetes": settings.ops_enable_kubernetes,
        "ops_allowed_services": settings.ops_allowed_services,
        "ops_command_timeout_seconds": settings.ops_command_timeout_seconds,
        "rate_limit_per_minute": settings.rate_limit_per_minute,
        "restart_required_fields": sorted(RESTART_REQUIRED_FIELDS),
    }


def _env_value(value: object) -> str:
    if isinstance(value, SecretStr):
        value = value.get_secret_value()
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, dict):
        payload = {
            key: item.model_dump(by_alias=True) if isinstance(item, BaseModel) else item
            for key, item in value.items()
        }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)


def persist_env(updates: dict[str, object], path: Path = Path(".env")) -> None:
    env_updates = {key.upper(): _env_value(value) for key, value in updates.items()}
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    seen: set[str] = set()
    output: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in line:
            output.append(line)
            continue
        key = line.split("=", 1)[0].strip()
        if key in env_updates:
            output.append(f"{key}={env_updates[key]}")
            seen.add(key)
        else:
            output.append(line)

    if output and output[-1] != "":
        output.append("")
    for key, value in env_updates.items():
        if key not in seen:
            output.append(f"{key}={value}")

    path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


def apply_settings(
    settings: Settings,
    request: PlatformSettingsUpdate,
    env_path: Path = Path(".env"),
) -> tuple[list[str], list[str]]:
    updates = request.model_dump(exclude_unset=True)
    clear_api_key = bool(updates.pop("clear_llm_api_key", False))

    if "llm_api_key" in updates and updates["llm_api_key"] == "":
        updates.pop("llm_api_key")
    if clear_api_key:
        updates["llm_api_key"] = ""

    updates = {key: value for key, value in updates.items() if key in CONFIGURABLE_FIELDS}
    if not updates:
        return [], []

    candidate_data = settings.model_dump()
    candidate_data.update(updates)
    candidate = Settings.model_validate(candidate_data)

    changed = [
        key
        for key in updates
        if getattr(settings, key) != getattr(candidate, key)
    ]
    if not changed:
        return [], []

    persisted = {key: getattr(candidate, key) for key in changed}
    persist_env(persisted, env_path)

    for key in changed:
        setattr(settings, key, getattr(candidate, key))

    restart_required = sorted(set(changed).intersection(RESTART_REQUIRED_FIELDS))
    return changed, restart_required
