from enum import Enum, auto


class AutoUpperName(Enum):
    def _generate_next_value_(name, start, count, last_values):
        return name.upper()


class AutoLowerName(Enum):
    def _generate_next_value_(name, start, count, last_values):
        return name.lower()


class OrderStatus(AutoUpperName):
    PENDING = auto()
    PROCESSING = auto()
    COMPLETED = auto()
    CANCELLED = auto()
    FAILED = auto()
    RETRYING = auto()
