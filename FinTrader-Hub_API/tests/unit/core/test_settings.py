from core.config import Settings, get_settings


def test_settings_load_from_env(monkeypatch) -> None:
    monkeypatch.setenv("APP_NAME", "FinTrader Test")
    monkeypatch.setenv("JWT_SECRET_KEY", "env-secret-key-with-minimum-32-chars")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "45")

    get_settings.cache_clear()
    settings = get_settings()

    assert settings.app_name == "FinTrader Test"
    assert settings.jwt_secret_key == "env-secret-key-with-minimum-32-chars"
    assert settings.access_token_expire_minutes == 45


def test_settings_defaults() -> None:
    settings = Settings()

    assert settings.jwt_algorithm == "HS256"
    assert settings.refresh_token_expire_days == 7
