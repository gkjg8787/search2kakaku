from pydantic import BaseModel, Field
from domain.models.pricelog import pricelog as m_pricelog


class ViewURLActive(BaseModel):
    id: int
    url: str
    is_active: bool | None = None
    sitename: str | None = None
    options: dict | None = None


class ViewURLResponse(BaseModel):
    view_urls: list[ViewURLActive] = Field(default_factory=list)


# New models for API requests
class URLRegisterRequest(BaseModel):
    urls: list[str] | None = None
    url_ids: list[int] | None = None
    sitename: str | None = None
    options: dict | None = None


class URLRemoveRequest(BaseModel):
    urls: list[str] | None = None
    url_ids: list[int] | None = None


class UpdateNotificationResult(BaseModel):
    update_type: str = Field(default="")
    updated_list: list[m_pricelog.URL] = Field(default_factory=list)
    added_list: list[m_pricelog.URL] = Field(default_factory=list)
    unregistered_list: list[str] = Field(default_factory=list)


class UpdateNotificationResultResponse(UpdateNotificationResult):
    pass


# New models for kakaku API
class KakakuItemCreateRequest(BaseModel):
    name: str = Field(..., description="新規に作成するアイテム名")
    urls: list[str] = Field(..., description="アイテムに追加するURLのリスト")


class KakakuItemCreateResponse(BaseModel):
    item_id: int | None = Field(None, description="作成されたアイテムのID")
    error_msg: str | None = Field(None, description="エラーメッセージ")


class KakakuItemAddURLRequest(BaseModel):
    item_id: int = Field(..., description="URLを追加する対象のアイテムID")
    urls: list[str] = Field(..., description="アイテムに追加するURLのリスト")


class KakakuURL(BaseModel):
    url: str
    url_id: int | None = Field(None)


class KakakuItemAddURLResponse(BaseModel):
    item_id: int | None = Field(None, description="更新されたアイテムのID")
    add_urls: list[KakakuURL] | None = Field(None, description="追加されたURLとURLのID")
    error_msg: str | None = Field(None, description="エラーメッセージ")


class KakakuItem(BaseModel):
    item_id: int
    name: str


class KakakuURLtoItem(KakakuURL):
    items: list[KakakuItem] = Field(default_factory=list)


class KakakuItemGetResponse(BaseModel):
    results: list[KakakuURLtoItem] = Field(default_factory=list)
    error_msg: str | None = Field(None, description="エラーメッセージ")


class KakakuListContext(BaseModel):
    results: list[KakakuURLtoItem] = Field(default_factory=list)
    error_msgs: list[str] = Field(default_factory=list)
    to_link: bool = Field(default=False)
    active_filter: str | None = Field(default=None)
