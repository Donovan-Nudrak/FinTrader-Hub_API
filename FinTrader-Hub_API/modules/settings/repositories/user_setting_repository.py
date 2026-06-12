from sqlalchemy import select
from sqlalchemy.orm import Session

from modules.settings.models.user_setting import UserSetting


class UserSettingRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, user_setting: UserSetting) -> UserSetting:
        self.db.add(user_setting)
        self.db.flush()
        self.db.refresh(user_setting)
        return user_setting

    def update(self, user_setting: UserSetting) -> UserSetting:
        self.db.add(user_setting)
        self.db.flush()
        self.db.refresh(user_setting)
        return user_setting

    def get_by_user_id(self, user_id: int) -> UserSetting | None:
        statement = select(UserSetting).where(UserSetting.user_id == user_id)
        return self.db.scalar(statement)
