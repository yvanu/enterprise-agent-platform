from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Enterprise Agent Platform"
    app_env: str = "development"

    database_url: str = "sqlite:///./data/demo.db"
    database_schema: str | None = None
    sql_max_rows: int = 200
    sql_timeout_seconds: int = 8

    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = ""
    embedding_model: str = ""
    llm_timeout_seconds: int = 60

    agent_max_attempts: int = 3
    knowledge_db_path: str = "./data/knowledge.db"
    knowledge_top_k: int = 5

    ops_log_files: str = ""
    prometheus_url: str = ""
    ops_http_timeout_seconds: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
