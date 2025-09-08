from common.enums import AutoLowerName, auto, Enum


class SiteName(AutoLowerName):
    SOFMAP = auto()
    GEO = auto()
    IOSYS = auto()


class SupportDomain(Enum):
    SOFMAP = "www.sofmap.com"
    A_SOFMAP = "a.sofmap.com"
    GEO = "ec.geo-online.co.jp"
    IOSYS = "iosys.co.jp"
