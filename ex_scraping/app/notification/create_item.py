import uuid

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from .util import create_api_url
from .enums import APIURLName
from .models import ItemCreate, ItemCreateResponse
from .factory import APIPathOptionFactory
from app.activitylog.update import UpdateActivityLog

ACTIVITY_TYPE = "create_item_with_api"


def create_request_model(item_name: str, urls: list[str]) -> ItemCreate:
    return ItemCreate(name=item_name, urls=urls)


async def send_itemname_and_urls_to_api(
    item_name: str, urls: list[str]
) -> tuple[bool, str, int | None]:
    apiopt = APIPathOptionFactory().create(apiurlname=APIURLName.ADD_ITEM)
    api_url = create_api_url(apiopt=apiopt)
    async with httpx.AsyncClient() as client:
        try:
            itemcreate = create_request_model(item_name=item_name, urls=urls)
            match apiopt.method.lower():
                case "post":
                    res = await client.post(
                        api_url, json=itemcreate.model_dump(mode="json")
                    )
                case "patch":
                    res = await client.patch(
                        api_url, json=itemcreate.model_dump(mode="json")
                    )
                case "get":
                    res = await client.get(
                        api_url, params=itemcreate.model_dump(mode="json")
                    )
                case _:
                    raise ValueError(f"no support method, {apiopt.method.lower()}")
            res.raise_for_status()
        except Exception as e:
            return False, f"failed to api, {e}", None
    res_json = res.json()
    if not isinstance(res_json, dict):
        return False, f"invalid type response, type:{type(res_json)}, {res_json}", None
    itemcreateresponse = ItemCreateResponse(**res_json)
    if not itemcreateresponse.item_id:
        return False, "failed to get item_id", None
    return True, "", itemcreateresponse.item_id


async def create_item_with_api(
    ses: AsyncSession,
    item_name: str,
    urls: list[str],
    log=None,
    caller_type: str | None = None,
):
    upactlog = UpdateActivityLog(ses=ses)
    init_subinfo = {
        "item_name": item_name,
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

    ok, msg, item_id = await send_itemname_and_urls_to_api(
        item_name=item_name, urls=urls
    )

    if ok:
        add_subinfo = {"item_id": item_id}
        await upactlog.completed(id=taskactlog_id, add_subinfo=add_subinfo)
        if log:
            log.info("create item with api ... ok", item_id=item_id)
    else:
        await upactlog.failed(id=taskactlog_id, error_msg=msg)
        if log:
            log.error("create item with api ... ng", error_msg=msg)
