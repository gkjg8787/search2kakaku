import uuid

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from common import read_config
from .util import create_api_url
from .enums import APIURLName
from .models import URLtoItemGetResponse
from .factory import APIPathOptionFactory
from app.activitylog.update import UpdateActivityLog

ACTIVITY_TYPE = "get_items_by_url_with_api"


async def get_items_with_api_url(
    url: str, timeout: float
) -> tuple[bool, str, URLtoItemGetResponse | None]:
    apiopt = APIPathOptionFactory().create(apiurlname=APIURLName.GET_ITEMS_BY_URL)
    api_url = create_api_url(apiopt=apiopt)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            match apiopt.method.lower():
                case "get":
                    res = await client.get(api_url, params={"url": url})
                case _:
                    raise ValueError(f"no support method, {apiopt.method.lower()}")
            res.raise_for_status()
        except Exception as e:
            return False, f"failed to api, type:{type(e).__name__}, {e}", None
    res_json = res.json()
    if not isinstance(res_json, dict):
        return False, f"invalid type response, type:{type(res_json)}, {res_json}", None
    urltoitemgetres = URLtoItemGetResponse(**res_json)
    if not urltoitemgetres.url_active.url_id:
        return False, "URL is not registered", urltoitemgetres
    if not urltoitemgetres.items:
        return False, "URL has no relation to item", urltoitemgetres
    return True, "", urltoitemgetres


async def get_items_by_url_with_api(
    ses: AsyncSession,
    urls: list[str],
    log=None,
    caller_type: str | None = None,
):
    upactlog = UpdateActivityLog(ses=ses)
    init_subinfo = {
        "urls": urls,
    }
    db_taskactlog = await upactlog.create(
        target_id=str(uuid.uuid4()),
        activity_type=ACTIVITY_TYPE,
        caller_type=caller_type,
        subinfo=init_subinfo,
    )
    taskactlog_id = db_taskactlog.id
    await upactlog.in_progress(id=taskactlog_id)

    results = []
    err_msgs = []
    for url in urls:
        ok, msg, response = await get_items_with_api_url(
            url=url, timeout=read_config.get_api_options().post_data.timeout
        )

        if response and response.items:
            items_dict = {item.item_id: item.name for item in response.items}
        else:
            items_dict = {}
        if response and response.url_active:
            res_dict = {"url_id": response.url_active.url_id, "items": items_dict}
        else:
            res_dict = {"url_id": None, "items": items_dict}
        if ok:
            if log:
                log.info("get items by url with api ... ok", response=res_dict)
        else:
            err_msgs.append(f"[{url}:{msg}]")
            if log:
                log.error(
                    "get items by url with api ... ng", error_msg=msg, response=res_dict
                )
        results.append(res_dict)
    add_subinfo = {"response": results}
    if not err_msgs:
        await upactlog.completed(id=taskactlog_id, add_subinfo=add_subinfo)
    elif len(err_msgs) == len(urls):
        await upactlog.failed(
            id=taskactlog_id, error_msg=",".join(err_msgs), add_subinfo=add_subinfo
        )
    else:
        await upactlog.completed_with_error(
            id=taskactlog_id, error_msg=",".join(err_msgs), add_subinfo=add_subinfo
        )
