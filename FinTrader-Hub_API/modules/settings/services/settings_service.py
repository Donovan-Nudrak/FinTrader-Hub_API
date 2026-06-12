from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from core.config import get_settings
from core.exceptions import NotFoundError, ValidationError
from modules.settings.models.api_key import ApiKey
from modules.settings.models.user_setting import UserSetting
from modules.settings.repositories import ApiKeyRepository, UserSettingRepository
from modules.settings.schemas.settings import (
    ApiKeyResponse,
    CreateApiKeyRequest,
    UpdateApiKeyRequest,
    UpdateUserSettingRequest,
    UserSettingResponse,
)


def mask_key_value(key_value: str) -> str:
    if not key_value:
        return "****"
    if len(key_value) <= 4:
        return "*" * len(key_value)
    return f"{key_value[:4]}{'*' * (len(key_value) - 4)}"


class SettingsService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.user_setting_repository = UserSettingRepository(db)
        self.api_key_repository = ApiKeyRepository(db)
        self.settings = get_settings()

    def get_user_settings(self, user_id: int) -> UserSettingResponse:
        user_setting = self.user_setting_repository.get_by_user_id(user_id)
        if user_setting is None:
            user_setting = self._create_default_user_settings(user_id)
            self.db.commit()
        return UserSettingResponse.model_validate(user_setting)

    def update_user_settings(
        self,
        user_id: int,
        request: UpdateUserSettingRequest,
    ) -> UserSettingResponse:
        user_setting = self.user_setting_repository.get_by_user_id(user_id)
        if user_setting is None:
            user_setting = self._create_default_user_settings(user_id)

        update_data = request.model_dump(exclude_unset=True)
        if not update_data:
            raise ValidationError("No fields provided for update")

        if "base_currency" in update_data and update_data["base_currency"] is not None:
            user_setting.base_currency = update_data["base_currency"].upper()

        if "timezone" in update_data:
            user_setting.timezone = update_data["timezone"]

        if "alert_email" in update_data:
            user_setting.alert_email = update_data["alert_email"]

        if (
            "dashboard_refresh_interval" in update_data
            and update_data["dashboard_refresh_interval"] is not None
        ):
            user_setting.dashboard_refresh_interval = update_data["dashboard_refresh_interval"]

        updated = self.user_setting_repository.update(user_setting)
        self.db.commit()
        return UserSettingResponse.model_validate(updated)

    def list_api_keys(self, user_id: int) -> list[ApiKeyResponse]:
        api_keys = self.api_key_repository.list_by_user_id(user_id)
        return [self._to_api_key_response(api_key) for api_key in api_keys]

    def create_api_key(self, user_id: int, request: CreateApiKeyRequest) -> ApiKeyResponse:
        encrypted_value = self._encrypt_key_value(request.key_value)
        api_key = ApiKey(
            user_id=user_id,
            name=request.name.strip(),
            provider=request.provider,
            key_value=encrypted_value,
            is_active=request.is_active,
        )
        created = self.api_key_repository.create(api_key)
        self.db.commit()
        return self._to_api_key_response(created, plain_key_value=request.key_value)

    def update_api_key(
        self,
        user_id: int,
        api_key_id: int,
        request: UpdateApiKeyRequest,
    ) -> ApiKeyResponse:
        api_key = self._get_owned_api_key(user_id, api_key_id)
        update_data = request.model_dump(exclude_unset=True)
        if not update_data:
            raise ValidationError("No fields provided for update")

        plain_key_value: str | None = None

        if "name" in update_data and update_data["name"] is not None:
            api_key.name = update_data["name"].strip()

        if "key_value" in update_data and update_data["key_value"] is not None:
            plain_key_value = update_data["key_value"]
            api_key.key_value = self._encrypt_key_value(plain_key_value)

        if "is_active" in update_data and update_data["is_active"] is not None:
            api_key.is_active = update_data["is_active"]

        updated = self.api_key_repository.update(api_key)
        self.db.commit()
        return self._to_api_key_response(updated, plain_key_value=plain_key_value)

    def delete_api_key(self, user_id: int, api_key_id: int) -> None:
        api_key = self._get_owned_api_key(user_id, api_key_id)
        self.api_key_repository.delete(api_key)
        self.db.commit()

    def decrypt_api_key_value(self, encrypted_value: str) -> str:
        fernet = self._get_fernet()
        try:
            return fernet.decrypt(encrypted_value.encode()).decode()
        except InvalidToken as exc:
            raise ValidationError("Stored API key could not be decrypted") from exc

    def _create_default_user_settings(self, user_id: int) -> UserSetting:
        user_setting = UserSetting(
            user_id=user_id,
            base_currency="USD",
            timezone="UTC",
            alert_email=None,
            dashboard_refresh_interval=300,
        )
        return self.user_setting_repository.create(user_setting)

    def _get_owned_api_key(self, user_id: int, api_key_id: int) -> ApiKey:
        api_key = self.api_key_repository.get_by_id_and_user_id(api_key_id, user_id)
        if api_key is None:
            raise NotFoundError("API key not found")
        return api_key

    def _get_fernet(self) -> Fernet:
        encryption_key = self.settings.api_key_encryption_key
        if not encryption_key:
            raise ValidationError("API key encryption is not configured")
        try:
            return Fernet(encryption_key.encode())
        except ValueError as exc:
            raise ValidationError("API key encryption key is invalid") from exc

    def _encrypt_key_value(self, key_value: str) -> str:
        fernet = self._get_fernet()
        return fernet.encrypt(key_value.encode()).decode()

    def _to_api_key_response(
        self,
        api_key: ApiKey,
        *,
        plain_key_value: str | None = None,
    ) -> ApiKeyResponse:
        if plain_key_value is not None:
            masked = mask_key_value(plain_key_value)
        else:
            decrypted = self.decrypt_api_key_value(api_key.key_value)
            masked = mask_key_value(decrypted)

        return ApiKeyResponse(
            id=api_key.id,
            user_id=api_key.user_id,
            name=api_key.name,
            provider=api_key.provider,
            masked_key_value=masked,
            is_active=api_key.is_active,
            last_used_at=api_key.last_used_at,
            created_at=api_key.created_at,
            updated_at=api_key.updated_at,
        )
