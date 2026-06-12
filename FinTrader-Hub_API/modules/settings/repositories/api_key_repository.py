from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.settings.models.api_key import ApiKey


class ApiKeyRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, api_key: ApiKey) -> ApiKey:
        self.db.add(api_key)
        self.db.flush()
        self.db.refresh(api_key)
        return api_key

    def update(self, api_key: ApiKey) -> ApiKey:
        self.db.add(api_key)
        self.db.flush()
        self.db.refresh(api_key)
        return api_key

    def delete(self, api_key: ApiKey) -> None:
        self.db.delete(api_key)
        self.db.flush()

    def get_by_id_and_user_id(self, api_key_id: int, user_id: int) -> ApiKey | None:
        statement = select(ApiKey).where(ApiKey.id == api_key_id, ApiKey.user_id == user_id)
        return self.db.scalar(statement)

    def list_by_user_id(self, user_id: int) -> list[ApiKey]:
        statement = (
            select(ApiKey)
            .where(ApiKey.user_id == user_id)
            .order_by(ApiKey.created_at.desc())
        )
        return list(self.db.scalars(statement).all())
