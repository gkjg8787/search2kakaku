from datetime import datetime

from pydantic import BaseModel


class ActivityLogGetCommand(BaseModel):
    id: int | None = None
    target_id: int | None = None
    target_table: str = ""
    activity_type: str = ""
    range_type: str = ""
    current_state: str = ""
    is_error: bool = False
    updated_at_start: datetime | None = None
    updated_at_end: datetime | None = None
