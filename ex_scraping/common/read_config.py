from pydantic import BaseModel, Field

import settings


class SeleniumOptions(BaseModel):
    remote_url: str


class SelenimuTimeoutOptions(BaseModel):
    page_load_timeout: int = Field(ge=2, le=100)
    tag_wait_timeout: int = Field(ge=1, le=99)


class SofmapOptions(BaseModel):
    selenium: SelenimuTimeoutOptions


class APIURLOtpions(BaseModel):
    base_url: str


class APISendingOptions(BaseModel):
    urls: APIURLOtpions


class SQLParams(BaseModel):
    drivername: str
    database: str
    username: str | None = None
    password: str | None = None
    host: str | None = None
    port: str | None = None


class DataBaseOptions(BaseModel):
    sync: SQLParams
    a_sync: SQLParams


def to_lower_keys(obj):
    if isinstance(obj, dict):
        # 新しい辞書を構築し、各キーを小文字に変換
        # 値が辞書の場合は再帰的にto_lower_keysを適用
        return {
            k.lower() if isinstance(k, str) else k: to_lower_keys(v)
            for k, v in obj.items()
        }
    elif isinstance(obj, list):
        # リストの場合は、各要素に対してto_lower_keysを適用
        return [to_lower_keys(elem) for elem in obj]
    else:
        # 辞書でもリストでもない場合はそのまま返す
        return obj


def get_selenium_options():
    lower_key_dict = to_lower_keys(settings.SELENIUM_OPTIONS)
    return SeleniumOptions(**lower_key_dict)


def get_sofmap_options():
    lower_key_dict = to_lower_keys(settings.SOFMAP_OPTIONS)
    return SofmapOptions(**lower_key_dict)


def get_api_sending_options():
    lower_key_dict = to_lower_keys(settings.API_SENDING_OPTIONS)
    return APISendingOptions(**lower_key_dict)


def get_databases():
    lower_key_dict = to_lower_keys(settings.DATABASES)
    return DataBaseOptions(**lower_key_dict)
