from common.enums import AutoLowerName, auto


class ConditionOptions(AutoLowerName):
    NEW = auto()
    USED = auto()
    A = auto()


class SortOptions(AutoLowerName):
    L = auto()
    H = auto()
    VH = auto()
    VL = auto()
