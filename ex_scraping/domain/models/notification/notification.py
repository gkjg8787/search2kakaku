from sqlmodel import Field

from domain.models.base_model import SQLBase


class URLNotification(SQLBase, table=True):
    url_id: int = Field(index=True)
    is_active: bool
