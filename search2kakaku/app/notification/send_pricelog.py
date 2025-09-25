from datetime import datetime, timezone, timedelta
import uuid
import asyncio

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from domain.models.pricelog import pricelog as m_pricelog, command as p_cmd
from databases.sql.util import get_async_session
from databases.sql.pricelog import repository as p_repo
from domain.models.notification import command as noti_cmd
from databases.sql.notification import repository as n_repo
from .enums import APIURLName
from .models import ParseInfosUpdate, ParseInfo, PriceUpdateResponse
from app.activitylog.update import UpdateActivityLog
from app.activitylog.util import (
    get_activitylog_latest,
    is_updating_urls_or_sending_to_api,
)
from .util import create_api_url
from .factory import APIPathOptionFactory
from . import constants as nofi_const


async def _convert_pricelog_to_parseinfo(
    ses: AsyncSession,
    pricelog_list: list[m_pricelog.PriceLog],
) -> ParseInfosUpdate:
    urlrepo = p_repo.URLRepository(ses=ses)
    shoprepo = p_repo.ShopRepository(ses=ses)
    parseinfos = ParseInfosUpdate()
    for pricelog in pricelog_list:
        url = await urlrepo.get(command=p_cmd.URLGetCommand(id=pricelog.url_id))
        shop = await shoprepo.get(command=p_cmd.ShopGetCommand(id=pricelog.shop_id))
        if not url or not shop:
            raise ValueError(f"url or shop is None, url:{url}, shop:{shop}")
        pinfo = ParseInfo(
            url=url.url,
            name=pricelog.title,
            price=pricelog.price,
            condition=pricelog.condition,
            taxin=True,
            on_sale=pricelog.on_sale,
            salename=pricelog.salename,
            timestamp=pricelog.created_at,
            is_success=pricelog.is_success,
            storename=shop.name,
        )
        parseinfos.infos.append(pinfo)
    return parseinfos


async def _send_to_api(ses: AsyncSession, pricelog_list: list[m_pricelog.PriceLog]):
    apiopt = APIPathOptionFactory().create(apiurlname=APIURLName.UPDATE_PRICE)
    api_url = create_api_url(apiopt=apiopt)
    try:
        parseinfos = await _convert_pricelog_to_parseinfo(
            ses=ses, pricelog_list=pricelog_list
        )
    except Exception as e:
        return False, f"data convert error, type:{type(e).__name__}, {e}"
    async with httpx.AsyncClient() as client:
        try:
            match apiopt.method.lower():
                case "post":
                    res = await client.post(
                        api_url, json=parseinfos.model_dump(mode="json")
                    )
                case "patch":
                    res = await client.patch(
                        api_url, json=parseinfos.model_dump(mode="json")
                    )
                case "get":
                    res = await client.get(
                        api_url, params=parseinfos.model_dump(mode="json")
                    )
                case _:
                    raise ValueError(f"no support method, {apiopt.method.lower()}")
            res.raise_for_status()
        except Exception as e:
            return False, f"failed to api, type:{type(e).__name__}, {e}"
    res_json = res.json()
    if isinstance(res_json, list):
        if not res_json or len(res_json) > 1:
            return False, f"no data response or no suppoert response , {res_json}"
        res_json = res_json[0]
    if not isinstance(res_json, dict):
        return False, f"invalid type response, type:{type(res_json)}, {res_json}"
    priceupres = PriceUpdateResponse(**res_json)
    return priceupres.ok, priceupres.error_msg


async def get_new_start_date(upactivitylog: UpdateActivityLog):
    """
    Create a new start time from the past update history.

    Generates a newer time than the previous ActivityLog update time.
    Add 1 microsecond to the most recent updated_at.

    Raises:
        ValueError: The database value type is not supported.
    """
    latest_actlog = await get_activitylog_latest(
        upactivitylog=upactivitylog, activity_types=[nofi_const.SEND_LOG_ACTIVITY_TYPE]
    )
    if not latest_actlog:
        return None
    new_start_date = latest_actlog.updated_at
    if isinstance(new_start_date, str):
        new_start_date = datetime.strptime(new_start_date, "%Y-%m-%d %H:%M:%S.%f")
        new_start_date = new_start_date.replace(tzinfo=timezone.utc)
        return new_start_date + timedelta(microseconds=1)
    if isinstance(new_start_date, datetime):
        if new_start_date.tzinfo:
            new_start_date = new_start_date.astimezone(tz=timezone.utc)
        else:
            new_start_date = new_start_date.replace(tzinfo=timezone.utc)
        return new_start_date + timedelta(microseconds=1)
    ValueError(
        f"new_start_date is not supported type:{type(new_start_date)}, value:{new_start_date}"
    )


async def _send_one_url_to_api(
    url_id: int,
    caller_type: str | None = None,
    start_utc_date: datetime | None = None,
    end_utc_date: datetime | None = None,
    init_subinfo: dict | None = None,
    log=None,
):
    async for ses in get_async_session():
        upactlog = UpdateActivityLog(ses=ses)
        urlrepo = p_repo.URLRepository(ses=ses)
        pricelogrepo = p_repo.PriceLogRepository(ses=ses)
        db_activitylog = await upactlog.create(
            target_id=str(url_id),
            target_table="URL",
            activity_type=nofi_const.SEND_LOG_ACTIVITY_TYPE,
            caller_type=caller_type,
            subinfo=init_subinfo,
        )
        activitylog_id = db_activitylog.id
        await upactlog.in_progress(id=activitylog_id)

        urlinfo = await urlrepo.get(command=p_cmd.URLGetCommand(id=url_id))
        if not urlinfo:
            errmsg = "URL is not found"
            await upactlog.canceled(id=activitylog_id, error_msg=errmsg)
            return {
                "url_id": url_id,
                "ok": False,
                "msg": errmsg,
                "result_details": {"error": errmsg},
            }

        target_pricelogs = await pricelogrepo.get(
            command=p_cmd.PriceLogGetCommand(
                url=urlinfo.url,
                start_utc_date=start_utc_date,
                end_utc_date=end_utc_date,
            )
        )
        if not target_pricelogs:
            errmsg = "PriceLog is None"
            await upactlog.canceled(id=activitylog_id, error_msg=errmsg)
            if log:
                log.warning("no length target_pricelogs, skip", url_id=url_id)
            return {
                "url_id": url_id,
                "ok": False,
                "msg": errmsg,
                "result_details": {"error": errmsg},
            }

        result_details = {"update_pricelog_ids": [p.id for p in target_pricelogs]}
        ok, msg = await _send_to_api(ses=ses, pricelog_list=target_pricelogs)
        if ok:
            await upactlog.completed(id=activitylog_id, add_subinfo=result_details)
            if log:
                log.info("send to api ... OK", url_id=url_id)
            return {"url_id": url_id, "ok": True, "result_details": result_details}

        await upactlog.failed(
            id=activitylog_id, error_msg=msg, add_subinfo=result_details
        )
        if log:
            log.error("send to api ... NG", url_id=url_id, error_msg=msg)

        result_details["error"] = msg
        return {
            "url_id": url_id,
            "ok": False,
            "msg": msg,
            "result_details": result_details,
        }


async def send_target_URLs_to_api(
    ses: AsyncSession,
    start_utc_date: datetime | None,
    end_utc_date: datetime | None,
    log=None,
    caller_type: str | None = None,
):
    upactlog = UpdateActivityLog(ses=ses)
    if await is_updating_urls_or_sending_to_api(updateactlog=upactlog):
        msg = "cancelled due to updating urls or sending to api."
        if log:
            log.warning(msg)
        return

    init_subinfo = {
        "start_utc_date": start_utc_date,
        "end_utc_date": end_utc_date,
    }
    if start_utc_date is None and end_utc_date is None:
        new_start_date = await get_new_start_date(upactivitylog=upactlog)
        if new_start_date:
            init_subinfo["new_start_utc_date"] = new_start_date
            start_utc_date = new_start_date
    db_taskactlog = await upactlog.create(
        target_id=str(uuid.uuid4()),
        activity_type=nofi_const.SEND_LOG_ACTIVITY_TYPE,
        caller_type=caller_type,
        subinfo=init_subinfo,
    )
    taskactlog_id = db_taskactlog.id
    await upactlog.in_progress(id=taskactlog_id)

    urlnotirepo = n_repo.URLNotificationRepository(ses=ses)
    urlnoti_list = await urlnotirepo.get(
        command=noti_cmd.URLNotificationGetCommand(is_active=True)
    )
    url_id_list = [urlnoti.id for urlnoti in urlnoti_list]

    tasks = [
        _send_one_url_to_api(
            url_id,
            caller_type=caller_type,
            start_utc_date=start_utc_date,
            end_utc_date=end_utc_date,
            init_subinfo=init_subinfo,
            log=log,
        )
        for url_id in url_id_list
    ]
    results = await asyncio.gather(*tasks)

    target_results = {}
    err_msgs = []
    err_ids = []
    for res in results:
        url_id = res["url_id"]
        target_results[url_id] = res.get("result_details", {})
        if not res["ok"]:
            msg = res["msg"]
            err_msgs.append("{" + f"{url_id}:{msg}" + "}")
            err_ids.append(url_id)

    add_subinfo = {"target_results": target_results}
    if not err_msgs:
        await upactlog.completed(id=taskactlog_id, add_subinfo=add_subinfo)
    elif len(err_ids) == len(url_id_list):
        await upactlog.failed(
            id=taskactlog_id, add_subinfo=add_subinfo, error_msg=",".join(err_msgs)
        )
    else:
        await upactlog.completed_with_error(
            id=taskactlog_id, add_subinfo=add_subinfo, error_msg=",".join(err_msgs)
        )
