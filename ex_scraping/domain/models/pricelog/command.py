from datetime import datetime

from pydantic import BaseModel


class PriceLogGetCommand(BaseModel):
    id: int | None = None
    url: str = ""
    start_utc_date: datetime | None = None
    end_utc_date: datetime | None = None
