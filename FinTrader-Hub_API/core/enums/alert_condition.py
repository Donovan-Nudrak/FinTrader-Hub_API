from enum import StrEnum


class AlertCondition(StrEnum):
    ABOVE = "ABOVE"
    BELOW = "BELOW"
    PERCENT_CHANGE = "PERCENT_CHANGE"
