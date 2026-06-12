from enum import StrEnum


class AssetType(StrEnum):
    STOCK = "STOCK"
    CRYPTO = "CRYPTO"
    FOREX = "FOREX"
    FUTURE = "FUTURE"
    OPTION = "OPTION"
    ETF = "ETF"
    INDEX = "INDEX"
