import logging
import os
import socket
import subprocess
import sys
import time
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.factory import create_app
from core.config import get_settings

PROJECT_ROOT = Path(__file__).resolve().parents[2]
logger = logging.getLogger(__name__)

DEFAULT_DATABASE_URL = "postgresql://fintrader:fintrader_secret@localhost:5432/fintraderhub"
POSTGRES_HOST = "localhost"
POSTGRES_PORT = 5432
POSTGRES_START_TIMEOUT_SECONDS = 90


def _mask_value(value: str, visible: int = 4) -> str:
    if not value:
        return "<empty>"
    if len(value) <= visible:
        return "*" * len(value)
    return f"{value[:visible]}{'*' * (len(value) - visible)}"


def _port_is_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _docker_is_available() -> bool:
    try:
        result = subprocess.run(
            ["docker", "info"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _compose_postgres_is_running() -> bool:
    try:
        result = subprocess.run(
            [
                "docker",
                "compose",
                "ps",
                "--status",
                "running",
                "--services",
                "--filter",
                "status=running",
            ],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        if result.returncode != 0:
            return False
        running_services = {line.strip() for line in result.stdout.splitlines() if line.strip()}
        return "postgres" in running_services
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def _wait_for_postgres(host: str = POSTGRES_HOST, port: int = POSTGRES_PORT) -> None:
    deadline = time.time() + POSTGRES_START_TIMEOUT_SECONDS
    while time.time() < deadline:
        if _port_is_open(host, port):
            return
        time.sleep(1)
    raise RuntimeError(
        f"PostgreSQL is not reachable at {host}:{port} after {POSTGRES_START_TIMEOUT_SECONDS}s"
    )


def _start_postgres_with_compose() -> None:
    if not _docker_is_available():
        pytest.skip("Docker is not available. Integration tests require Docker Compose.")

    logger.info("PostgreSQL is not running. Starting docker compose service: postgres")
    result = subprocess.run(
        ["docker", "compose", "up", "-d", "postgres"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Failed to start PostgreSQL with docker compose.\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    _wait_for_postgres()


def _ensure_postgres_running() -> None:
    if _port_is_open(POSTGRES_HOST, POSTGRES_PORT):
        logger.info("PostgreSQL is reachable at %s:%s", POSTGRES_HOST, POSTGRES_PORT)
        return
    if _compose_postgres_is_running():
        logger.info("Docker Compose reports postgres running; waiting for port readiness")
        _wait_for_postgres()
        return
    _start_postgres_with_compose()


def _configure_integration_env() -> str:
    database_url = os.environ.get("TEST_DATABASE_URL", DEFAULT_DATABASE_URL)
    os.environ["POSTGRES_HOST"] = POSTGRES_HOST
    os.environ["DATABASE_URL"] = database_url
    os.environ.setdefault("SKIP_STARTUP_VALIDATION", "true")
    os.environ.setdefault("SKIP_AUTO_MIGRATIONS", "true")
    os.environ.setdefault("RESEND_API_KEY", "re_test_key")
    os.environ.setdefault("RESEND_FROM_EMAIL", "onboarding@resend.dev")
    os.environ.setdefault("ALERT_EMAIL", "test@example.com")
    get_settings.cache_clear()
    return database_url


def _rebind_database_session(database_url: str) -> None:
    import infrastructure.database.session as db_session

    engine = create_engine(database_url, pool_pre_ping=True)
    db_session.engine = engine
    db_session.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info("Database session rebound to %s", database_url)


def _run_alembic_migrations() -> None:
    logger.info("Applying Alembic migrations for integration tests")
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=PROJECT_ROOT,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Alembic migration failed during integration test setup.\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
    logger.info("Alembic migrations applied successfully")


@pytest.fixture(scope="session", autouse=True)
def integration_database() -> None:
    _ensure_postgres_running()
    database_url = _configure_integration_env()
    _rebind_database_session(database_url)
    _run_alembic_migrations()
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def _unique_credentials() -> dict[str, str]:
    suffix = uuid.uuid4().hex[:8]
    return {
        "email": f"user_{suffix}@example.com",
        "username": f"user_{suffix}",
        "password": "SecurePass123!",
    }


def register_and_login(client: TestClient, credentials: dict[str, str] | None = None) -> dict[str, str]:
    payload = credentials or _unique_credentials()
    register_response = client.post("/auth/register", json=payload)
    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def app_client() -> TestClient:
    get_settings.cache_clear()
    return TestClient(create_app())


@pytest.fixture
def auth_headers(app_client: TestClient) -> dict[str, str]:
    return register_and_login(app_client)
