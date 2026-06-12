from cryptography.fernet import Fernet

from modules.settings.services.settings_service import mask_key_value


def test_mask_key_value_shows_first_four_chars() -> None:
    assert mask_key_value("abcdefghij") == "abcd******"


def test_mask_key_value_short_key() -> None:
    assert mask_key_value("abc") == "***"


def test_encrypt_decrypt_roundtrip() -> None:
    from cryptography.fernet import Fernet as FernetClass

    key = FernetClass.generate_key().decode()

    class _Settings:
        api_key_encryption_key = key

    from modules.settings.services import settings_service as settings_module

    original_get_settings = settings_module.get_settings
    settings_module.get_settings = lambda: _Settings()  # type: ignore[assignment]

    try:
        service = settings_module.SettingsService(db=None)  # type: ignore[arg-type]
        encrypted = service._encrypt_key_value("super-secret-key")
        decrypted = service.decrypt_api_key_value(encrypted)
        assert decrypted == "super-secret-key"
        assert encrypted != "super-secret-key"
    finally:
        settings_module.get_settings = original_get_settings
