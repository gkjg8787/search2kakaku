import uuid

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from .util import create_api_url
from .enums import APIURLName
from .models import ItemsURLCreate, ItemsURLCreateResponse, URLActive
from .factory import APIPathOptionFactory
from app.activitylog.update import UpdateActivityLog

ACTIVITY_TYPE = "add_urls_to_item_with_api"


def create_request_model(item_id: int, urls: list[str]) -> ItemsURLCreate:
    return ItemsURLCreate(
        item_id=item_id,
        url_actives=[URLActive(url=url, is_active=True) for url in urls],
    )


async def send_urls_to_api_item(
    item_id: int, urls: list[str]
) -> tuple[bool, str, ItemsURLCreateResponse | None]:
    apiopt = APIPathOptionFactory().create(apiurlname=APIURLName.ADD_URL_TO_ITEM)
    api_url = create_api_url(apiopt=apiopt)
    async with httpx.AsyncClient() as client:
        try:
            itemsurlcreate = create_request_model(item_id=item_id, urls=urls)
            match apiopt.method.lower():
                case "post":
                    res = await client.post(
                        api_url, json=itemsurlcreate.model_dump(mode="json")
                    )
                case "patch":
                    res = await client.patch(
                        api_url, json=itemsurlcreate.model_dump(mode="json")
                    )
                case "get":
                    res = await client.get(
                        api_url, params=itemsurlcreate.model_dump(mode="json")
                    )
                case _:
                    raise ValueError(f"no support method, {apiopt.method.lower()}")
            res.raise_for_status()
        except Exception as e:
            return False, f"failed to api, {e}", None
    res_json = res.json()
    if not isinstance(res_json, dict):
        return False, f"invalid type response, type:{type(res_json)}, {res_json}", None
    itemsurlcreateres = ItemsURLCreateResponse(**res_json)
    msg = ""
    for urlact in itemsurlcreateres.url_actives:
        if not urlact.url_id:
            if msg:
                msg += ","
            msg += f"[{urlact.url}:failed to get url_id]"
    if msg:
        return False, msg, itemsurlcreateres
    return True, "", itemsurlcreateres


async def add_urls_to_item_with_api(
    ses: AsyncSession,
    item_id: int,
    urls: list[str],
    log=None,
    caller_type: str | None = None,
):
    upactlog = UpdateActivityLog(ses=ses)
    init_subinfo = {
        "item_id": item_id,
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

    ok, msg, response = await send_urls_to_api_item(item_id=item_id, urls=urls)
    if response:
        res_dict = {url.url: url.url_id for url in response.url_actives}
    else:
        res_dict = {}
    add_subinfo = {"response": res_dict}
    if ok:
        await upactlog.completed(id=taskactlog_id, add_subinfo=add_subinfo)
        if log:
            log.info("add urls to item with api ... ok", response=res_dict)
    else:
        await upactlog.failed(id=taskactlog_id, error_msg=msg)
        if log:
            log.error("add urls to item with api ... ng", error_msg=msg)
