from enum import auto
from common.enums import AutoUpperName


class NotificationType(AutoUpperName):
    API = auto()


class RangeType(AutoUpperName):
    ALL = auto()
    TODAY = auto()
