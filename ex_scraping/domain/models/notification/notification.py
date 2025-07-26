from sqlmodel import Field

from domain.models.base_model import SQLBase

from common import constants, enums


class LogUpdateNotification(SQLBase, table=True):
    target_entity_id: str
    notification_type: str = Field(description="通知の方法。APIなど")
    range_type: str = Field(description="更新データの範囲。本日など")
    current_state: str = Field(default=enums.OrderStatus.PENDING.name, index=True)
    error_msg: str = Field(default="")
    retry_count: int = Field(default=constants.INIT_COUNT)


class URLNotification(SQLBase, table=True):
    url_id: int = Field(index=True)
    is_active: bool
