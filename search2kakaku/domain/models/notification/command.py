from pydantic import BaseModel


class URLNotificationGetCommand(BaseModel):
    url_id: int | None = None
    is_active: bool | None = None


class URLUpdateParameterGetCommand(BaseModel):
    url_id: int | None = None
    sitename: str | None = None
