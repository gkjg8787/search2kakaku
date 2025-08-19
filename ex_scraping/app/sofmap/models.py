from pydantic import BaseModel


class SofmapSearchDataOptions(BaseModel):
    is_akiba: bool | None = None
    direct_search: bool | None = None
    gid: str | None = None
    product_type: str | None = None
    display_count: int | None = None
    order_by: str | None = None
    remove_duplicates: bool | None = None
