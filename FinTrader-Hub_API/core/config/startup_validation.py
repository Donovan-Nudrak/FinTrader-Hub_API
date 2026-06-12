from cryptography.fernet import Fernet

from core.config.settings import Settings


class StartupValidationError(Exception):
    pass


def validate_startup_settings(settings: Settings) -> None:
    if settings.skip_startup_validation:
        return

    errors: list[str] = []

    if not settings.database_url.startswith("postgresql://"):
        errors.append("DATABASE_URL must start with postgresql://")

    if not settings.jwt_secret_key or len(settings.jwt_secret_key) < 32:
        errors.append("JWT_SECRET_KEY must be at least 32 characters")

    if not settings.resend_api_key.strip():
        errors.append("RESEND_API_KEY is required and cannot be empty")

    if not settings.resend_from_email.strip():
        errors.append("RESEND_FROM_EMAIL is required and cannot be empty")

    if not settings.alert_email.strip():
        errors.append("ALERT_EMAIL is required and cannot be empty")

    if not settings.api_key_encryption_key.strip():
        errors.append("API_KEY_ENCRYPTION_KEY is required and cannot be empty")
    else:
        try:
            Fernet(settings.api_key_encryption_key.encode())
        except Exception as exc:
            errors.append(f"API_KEY_ENCRYPTION_KEY must be a valid Fernet key: {exc}")

    if errors:
        message = "Startup validation failed:\n- " + "\n- ".join(errors)
        raise StartupValidationError(message)
