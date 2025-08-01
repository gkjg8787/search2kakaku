from sqlmodel import Field
from sqlalchemy import JSON, Column
from sqlalchemy.ext.mutable import MutableDict

from domain.models.base_model import SQLBase
from common import constants, enums


class ActivityLog(SQLBase, table=True):
    target_id: str
    target_table: str
    activity_type: str = Field(index=True, description="通知の方法。APIなど")
    range_type: str = Field(description="対象データの範囲。本日など")
    current_state: str = Field(default=enums.OrderStatus.PENDING.name, index=True)
    meta: dict = Field(
        default_factory=dict, sa_column=Column(MutableDict.as_mutable(JSON))
    )
    error_msg: str = Field(default="")
