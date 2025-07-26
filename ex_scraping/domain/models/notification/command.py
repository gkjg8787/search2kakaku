from pydantic import BaseModel


class LogUpdateNotificationGetCommand(BaseModel):
    id: int | None = None
    target_entity_id: str = ""
    notification_type: str = ""
    range_type: str = ""


class URLNotificationGetCommand(BaseModel):
    url_id: int | None = None
    is_active: bool | None = None
