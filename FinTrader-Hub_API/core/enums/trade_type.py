from enum import StrEnum


class TradeType(StrEnum):
    BUY = "BUY"
    SELL = "SELL"
    SHORT = "SHORT"
    COVER = "COVER"
