from common.enums import AutoUpperName, auto


class ProductTypeOptions(AutoUpperName):
    NEW = auto()
    USED = auto()
    ALL = auto()


class OrderByOptions(AutoUpperName):
    DEFAULT = auto()
    SALES_DESC = auto()
    PRICE_ASC = auto()
    PRICE_DESC = auto()
    NAME_ASC = auto()
    MAKER_ASC = auto()
    DATE_DESC = auto()
    DATE_ASC = auto()

    @classmethod
    def is_name_in_enum(cls, name: str) -> bool:
        return name.upper() in cls.__members__
