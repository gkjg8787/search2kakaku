from urllib.parse import urlencode, quote

from .constants import BASE_SEARCH_URL, SHIFT_JIS


def build_search_url(
    search_keyword: str,
    base_url: str = BASE_SEARCH_URL,
    query_encode_type: str = SHIFT_JIS,
    gid: str = "",
    product_type: str = "",
) -> str:
    search_query = f"keyword={quote(search_keyword, encoding=query_encode_type)}"
    param = {
        "gid": gid,
    }
    product_types = ["NEW", "USED"]
    if product_type and product_type.upper() in product_types:
        param["product_type"] = product_type.upper()
    final_url = f"{base_url}?{urlencode(param)}&{search_query}"
    return final_url
