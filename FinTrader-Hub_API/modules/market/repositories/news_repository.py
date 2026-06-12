from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from modules.market.models.news import News


class NewsRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create(self, news: News) -> News:
        self.db.add(news)
        self.db.flush()
        self.db.refresh(news)
        return news

    def exists_by_url(self, url: str) -> bool:
        statement = select(News.id).where(News.url == url)
        return self.db.scalar(statement) is not None

    def exists_by_asset_title_published_at(
        self,
        asset_id: int,
        title: str,
        published_at: datetime,
    ) -> bool:
        statement = select(News.id).where(
            News.asset_id == asset_id,
            News.title == title,
            News.published_at == published_at,
        )
        return self.db.scalar(statement) is not None

    def list_by_asset_id(self, asset_id: int) -> list[News]:
        statement = (
            select(News)
            .where(News.asset_id == asset_id)
            .order_by(News.published_at.desc())
        )
        return list(self.db.scalars(statement).all())

    def delete_expired(self, cutoff: datetime) -> int:
        statement = delete(News).where(News.published_at < cutoff)
        result = self.db.execute(statement)
        self.db.flush()
        return int(result.rowcount or 0)
