import pytest

from app.core.config import Settings, validate_settings
from app.platform.llm import OpenAICompatibleLLM


def test_production_requires_auth_and_non_demo_tokens():
    with pytest.raises(ValueError, match="生产环境必须启用"):
        validate_settings(Settings(app_env="production"))

    with pytest.raises(ValueError, match="示例 AUTH_TOKENS"):
        validate_settings(
            Settings(
                app_env="production",
                auth_enabled=True,
                auth_tokens={"admin-token": "admin:admin"},
            )
        )

    validate_settings(
        Settings(
            app_env="production",
            auth_enabled=True,
            auth_tokens={"5b816798af9147cf": "admin:admin"},
        )
    )


def test_auth_enabled_requires_tokens():
    with pytest.raises(ValueError, match="必须配置 AUTH_TOKENS"):
        validate_settings(Settings(auth_enabled=True))


def test_secret_settings_are_not_exposed_in_repr():
    settings = Settings(
        auth_tokens={"top-secret-token": "admin:admin"},
        llm_api_key="top-secret-key",
    )

    value = repr(settings)
    assert "top-secret-token" not in value
    assert "top-secret-key" not in value
    assert settings.llm_api_key.get_secret_value() == "top-secret-key"
    assert OpenAICompatibleLLM(settings)._headers() == {
        "Authorization": "Bearer top-secret-key"
    }
