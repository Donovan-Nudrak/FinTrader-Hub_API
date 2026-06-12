from enum import StrEnum


class ApiKeyProvider(StrEnum):
    FINNHUB = "FINNHUB"
    COINGECKO = "COINGECKO"
    ALPHA_VANTAGE = "ALPHA_VANTAGE"
    EXCHANGE_RATE = "EXCHANGE_RATE"
