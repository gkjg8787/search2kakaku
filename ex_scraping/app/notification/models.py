from datetime import datetime, timezone

from pydantic import BaseModel, Field

from common import constants as cmn_const


class APIPathOption(BaseModel):
    name: str
    path: str
    method: str


class ParseInfo(BaseModel):
    url: str = ""
    name: str = ""
    price: int = cmn_const.NONE_PRICE
    condition: str = ""
    taxin: bool = False
    on_sale: bool = False
    salename: str = ""
    timestamp: datetime | None = None
    is_success: bool = False
    storename: str = ""


class ParseInfos(BaseModel):
    infos: list[ParseInfo] = Field(default_factory=list)


class ParseInfosUpdate(ParseInfos):
    pass


class PriceUpdateResponse(BaseModel):
    ok: bool
    error_msg: str
