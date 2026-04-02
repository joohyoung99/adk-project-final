import importlib

import app.config.settings as settings_module


def _reload_settings_module():
    return importlib.reload(settings_module)


def test_settings_reads_env_values(monkeypatch) -> None:
    monkeypatch.setenv("MODEL_GEMINI_2_5_FLASH", "gemini-test")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "demo-project")
    monkeypatch.setenv("GOOGLE_CLOUD_LOCATION", "asia-northeast3")

    reloaded = _reload_settings_module()
    settings = reloaded.Settings()

    assert settings.model == "gemini-test"
    assert settings.google_cloud_project == "demo-project"
    assert settings.google_cloud_location == "asia-northeast3"


def test_settings_uses_defaults_when_env_missing(monkeypatch) -> None:
    monkeypatch.delenv("MODEL_GEMINI_2_5_FLASH", raising=False)
    monkeypatch.delenv("GOOGLE_CLOUD_LOCATION", raising=False)

    reloaded = _reload_settings_module()
    settings = reloaded.Settings()

    assert settings.model == "gemini-2.5-flash"
    assert settings.google_cloud_location == "us-central1"
