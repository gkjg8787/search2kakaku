import json
from urllib.parse import urlparse, urljoin

from fastapi.templating import Jinja2Templates

from common.read_config import get_html_options, get_api_options

templates = Jinja2Templates(directory="templates")


def custom_tojson_japanese(value, indent=None):
    """
    PythonオブジェクトをJSON文字列に変換し、
    日本語のエスケープを防ぎつつ、インデントを設定する。
    """
    # ensure_ascii=False で日本語のエスケープを防ぐ
    # indent=None の場合はインデントなし
    return json.dumps(value, ensure_ascii=False, indent=indent)


htmlopts = get_html_options()
apiopts = get_api_options()


def create_tokakaku_link(id):
    if not htmlopts.kakaku.to_link:
        return ""
    if not htmlopts.kakaku.base_url:
        return ""
    if htmlopts.kakaku.base_url == "post_data":
        base_url = apiopts.post_data.url.removesuffix("/api/").removesuffix("/api")
    else:
        base_url = htmlopts.kakaku.base_url
    base_url = urljoin(base_url, "users/items/v/")
    parsed_url = urlparse(base_url)
    return parsed_url._replace(query=f"itemid={id}").geturl()


templates.env.filters["tojson_japanese"] = custom_tojson_japanese
templates.env.filters["tokakaku_link"] = create_tokakaku_link
