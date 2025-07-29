from sqlmodel import Field
from sqlalchemy import JSON, Column
from sqlalchemy.ext.mutable import MutableDict

from domain.models.base_model import SQLBase
from common import constants, enums


class LogUpdateNotification(SQLBase, table=True):
    target_entity_id: str
    target_entity_type: str = Field(
        index=True, description="ログ対象の型、種類。URLなど"
    )
    notification_type: str = Field(description="通知の方法。APIなど")
    range_type: str = Field(description="更新データの範囲。本日など")
    current_state: str = Field(default=enums.OrderStatus.PENDING.name, index=True)
    meta: dict = Field(
        default_factory=dict, sa_column=Column(MutableDict.as_mutable(JSON))
    )
    error_msg: str = Field(default="")
    retry_count: int = Field(default=constants.INIT_COUNT)


class URLNotification(SQLBase, table=True):
    url_id: int = Field(index=True)
    is_active: bool
