from datetime import datetime

from pydantic import BaseModel


class PriceLogGetCommand(BaseModel):
    id: int | None = None
    url: str = ""
    start_utc_date: datetime | None = None
    end_utc_date: datetime | None = None


class URLGetCommand(BaseModel):
    id: int | None = None
    url: str = ""


class ShopGetCommand(BaseModel):
    id: int | None = None
    name: str = ""
