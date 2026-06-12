from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal


@dataclass
class NormalizedPrice:
    price: Decimal
    source: str
    timestamp: datetime


@dataclass
class NormalizedNewsItem:
    title: str
    summary: str | None
    source: str
    url: str
    published_at: datetime
