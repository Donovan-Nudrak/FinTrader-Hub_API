import os

import pytest
from cryptography.fernet import Fernet
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.config import Settings, get_settings
from core.dependencies import get_db, get_settings_dependency
from core.exceptions import NotFoundError, register_exception_handlers
from core.schemas import APIResponse

TEST_FERNET_KEY = Fernet.generate_key().decode()


@pytest.fixture(scope="session", autouse=True)
def configure_test_environment() -> None:
    os.environ.setdefault("SKIP_STARTUP_VALIDATION", "true")
    os.environ.setdefault("SKIP_AUTO_MIGRATIONS", "true")
    os.environ.setdefault("API_KEY_ENCRYPTION_KEY", TEST_FERNET_KEY)
    os.environ.setdefault("RESEND_API_KEY", "re_test_key")
    os.environ.setdefault("RESEND_FROM_EMAIL", "onboarding@resend.dev")
    os.environ.setdefault("ALERT_EMAIL", "test@example.com")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        jwt_secret_key="test-secret-key-with-minimum-32-characters",
        access_token_expire_minutes=15,
        refresh_token_expire_days=3,
        skip_startup_validation=True,
        api_key_encryption_key=TEST_FERNET_KEY,
        resend_api_key="re_test_key",
        resend_from_email="onboarding@resend.dev",
        alert_email="test@example.com",
    )


@pytest.fixture
def test_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/raise-not-found")
    def raise_not_found() -> None:
        raise NotFoundError("Item not found")

    @app.get("/settings-check")
    def settings_check(settings: Settings = Depends(get_settings_dependency)) -> dict:
        return {"app_name": settings.app_name}

    @app.get("/db-check")
    def db_check(_: Session = Depends(get_db)) -> dict:
        return {"db_dependency": "ok"}

    @app.get("/response-check")
    def response_check() -> APIResponse[dict]:
        return APIResponse(message="ok", data={"value": 1})

    return app


@pytest.fixture
def client(test_app: FastAPI) -> TestClient:
    return TestClient(test_app)


@pytest.fixture(autouse=True)
def clear_settings_cache() -> None:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
