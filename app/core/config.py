from functools import lru_cache

from pydantic import BaseModel, ConfigDict, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class DataSourceConfig(BaseModel):
    url: str
    schema_name: str | None = Field(default=None, alias="schema")

    model_config = ConfigDict(populate_by_name=True)


class Settings(BaseSettings):
    app_name: str = "Enterprise Agent Platform"
    app_env: str = "development"
    auth_enabled: bool = False
    auth_tokens: dict[str, str] = Field(default_factory=dict, repr=False)
    rate_limit_per_minute: int = Field(default=0, ge=0, le=100000)

    database_url: str = "sqlite:///./data/demo.db"
    database_schema: str | None = None
    data_sources: dict[str, DataSourceConfig] = Field(default_factory=dict)
    sql_max_rows: int = 200
    sql_timeout_seconds: int = 8

    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: SecretStr = SecretStr("")
    llm_model: str = ""
    embedding_model: str = ""
    llm_timeout_seconds: int = 60

    agent_max_attempts: int = 3
    knowledge_db_path: str = "./data/knowledge.db"
    knowledge_top_k: int = 5
    knowledge_max_upload_bytes: int = 10 * 1024 * 1024

    ops_log_files: str = ""
    prometheus_url: str = ""
    ops_http_timeout_seconds: int = 5
    ops_enable_docker: bool = False
    ops_enable_kubernetes: bool = False
    ops_allowed_services: str = ""
    ops_command_timeout_seconds: int = 5

    platform_db_path: str = "./data/platform.db"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


DEMO_AUTH_TOKENS = {"user-token", "operator-token", "approver-token", "admin-token"}
VALID_ROLES = {"user", "operator", "approver", "admin"}


def validate_settings(settings: Settings) -> None:
    errors: list[str] = []
    environment = settings.app_env.lower()
    production = environment in {"prod", "production"}

    if settings.auth_enabled and not settings.auth_tokens:
        errors.append("AUTH_ENABLED=true 时必须配置 AUTH_TOKENS")
    if production and not settings.auth_enabled:
        errors.append("生产环境必须启用 AUTH_ENABLED")

    for identity in settings.auth_tokens.values():
        username, separator, role = identity.partition(":")
        if not separator or not username or role not in VALID_ROLES:
            errors.append("AUTH_TOKENS 值必须使用 username:role 且 role 有效")
            break

    if production and DEMO_AUTH_TOKENS.intersection(settings.auth_tokens):
        errors.append("生产环境不能使用示例 AUTH_TOKENS")

    if errors:
        raise ValueError("配置检查失败: " + "; ".join(errors))


@lru_cache
def get_settings() -> Settings:
    return Settings()
