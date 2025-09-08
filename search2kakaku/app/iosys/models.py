from pydantic import BaseModel


class IosysSearchDataOptions(BaseModel):
    condition: str | None = None
    sort: str | None = None
    min_price: int | None = None
    max_price: int | None = None
