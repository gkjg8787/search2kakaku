from sqlmodel import Field
from sqlalchemy import JSON, Column
from sqlalchemy.ext.mutable import MutableDict

from domain.models.base_model import SQLBase


class URLNotification(SQLBase, table=True):
    url_id: int = Field(index=True)
    is_active: bool


class URLUpdateParameter(SQLBase, table=True):
    url_id: int = Field(index=True)
    sitename: str = Field(default="")
    meta: dict = Field(
        default_factory=dict, sa_column=Column(MutableDict.as_mutable(JSON))
    )
