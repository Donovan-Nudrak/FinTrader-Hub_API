import pytest
from cryptography.fernet import Fernet

from core.config import Settings
from core.config.startup_validation import StartupValidationError, validate_startup_settings


def _valid_settings(**overrides) -> Settings:
    defaults = {
        "database_url": "postgresql://user:pass@localhost:5432/db",
        "jwt_secret_key": "x" * 32,
        "resend_api_key": "re_test",
        "resend_from_email": "sender@resend.dev",
        "alert_email": "alerts@example.com",
        "api_key_encryption_key": Fernet.generate_key().decode(),
        "skip_startup_validation": False,
    }
    defaults.update(overrides)
    return Settings(**defaults)


def test_startup_validation_passes_with_valid_settings() -> None:
    validate_startup_settings(_valid_settings())


def test_startup_validation_fails_without_resend_api_key() -> None:
    with pytest.raises(StartupValidationError, match="RESEND_API_KEY"):
        validate_startup_settings(_valid_settings(resend_api_key=""))


def test_startup_validation_fails_with_invalid_fernet_key() -> None:
    with pytest.raises(StartupValidationError, match="Fernet"):
        validate_startup_settings(_valid_settings(api_key_encryption_key="not-a-fernet-key"))


def test_startup_validation_skipped_when_flag_set() -> None:
    validate_startup_settings(
        _valid_settings(
            resend_api_key="",
            skip_startup_validation=True,
        )
    )
