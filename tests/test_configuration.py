from app.core.config import Settings
from app.platform.configuration import PlatformSettingsUpdate, apply_settings, settings_view


def test_settings_view_masks_llm_api_key():
    settings = Settings(llm_api_key="super-secret", llm_model="demo-model")
    view = settings_view(settings)

    assert view["llm_api_key_configured"] is True
    assert "super-secret" not in repr(view)


def test_apply_settings_updates_runtime_and_persists_env(tmp_path):
    settings = Settings()
    env_path = tmp_path / ".env"

    changed, restart_required = apply_settings(
        settings,
        PlatformSettingsUpdate(
            llm_base_url="https://example.test/v1",
            llm_api_key="secret-key",
            llm_model="chat-model",
            embedding_model="embed-model",
            knowledge_top_k=9,
            database_url="sqlite:///./data/other.db",
        ),
        env_path,
    )

    assert settings.llm_base_url == "https://example.test/v1"
    assert settings.llm_api_key.get_secret_value() == "secret-key"
    assert settings.llm_model == "chat-model"
    assert settings.embedding_model == "embed-model"
    assert settings.knowledge_top_k == 9
    assert "database_url" in restart_required
    assert {"llm_model", "embedding_model", "knowledge_top_k"}.issubset(changed)

    persisted = env_path.read_text(encoding="utf-8")
    assert 'LLM_MODEL="chat-model"' in persisted
    assert 'LLM_API_KEY="secret-key"' in persisted
    assert "KNOWLEDGE_TOP_K=9" in persisted
