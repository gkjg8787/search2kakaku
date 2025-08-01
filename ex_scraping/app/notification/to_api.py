import os
from datetime import datetime, timezone, timedelta
import uuid

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from domain.models.pricelog import pricelog as m_pricelog, command as p_cmd
from databases.sqldb.pricelog import repository as p_repo
from domain.models.notification import command as noti_cmd
from databases.sqldb.notification import repository as n_repo
from domain.models.activitylog import command as act_cmd, enums as act_enums
from common.read_config import get_api_sending_options
from .constants import API_OPTIONS
from .enums import APIURLName
from .models import ParseInfosUpdate, ParseInfo, PriceUpdateResponse, APIPathOption
from app.update.update_activitylog import UpdateActivityLog

ACTIVITY_TYPE = "send_target_URLs_to_api"


async def convert_pricelog_to_parseinfo(
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


def get_api_base_url():
    apisendopt = get_api_sending_options()
    return apisendopt.urls.base_url


async def send_to_api(ses: AsyncSession, pricelog_list: list[m_pricelog.PriceLog]):
    name = APIURLName.UPDATE_PRICE.value
    apiopt = APIPathOption(name=name, **API_OPTIONS[name])
    base_url = get_api_base_url()
    api_url = os.path.join(base_url, apiopt.path)

    try:
        parseinfos = await convert_pricelog_to_parseinfo(
            ses=ses, pricelog_list=pricelog_list
        )
    except Exception as e:
        return False, f"data convert error, {e}"
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
            return False, f"failed to api, {e}"
    res_json = res.json()
    if isinstance(res_json, list):
        if not res_json or len(res_json) > 1:
            return False, f"no data response or no suppoert response , {res_json}"
        res_json = res_json[0]
    if not isinstance(res_json, dict):
        return False, f"invalid type response, type:{type(res_json)}, {res_json}"
    priceupres = PriceUpdateResponse(**res_json)
    return priceupres.ok, priceupres.error_msg


async def get_activitylog_latest(upactivitylog: UpdateActivityLog, activity_type: str):
    db_actlogs = await upactivitylog.get_all(
        command=act_cmd.ActivityLogGetCommand(activity_type=activity_type)
    )
    if not db_actlogs:
        return None
    lastest_actlog = max(db_actlogs, key=lambda log: log.updated_at)
    return lastest_actlog


async def get_new_start_date(upactivitylog: UpdateActivityLog):
    """
    Create a new start time from the past update history.

    Generates a newer time than the previous ActivityLog update time.
    Add 1 microsecond to the most recent updated_at.

    Raises:
        ValueError: The database value type is not supported.
    """
    latest_actlog = await get_activitylog_latest(
        upactivitylog=upactivitylog, activity_type=ACTIVITY_TYPE
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


async def send_target_URLs_to_api(
    ses: AsyncSession,
    start_utc_date: datetime | None,
    end_utc_date: datetime | None,
    log=None,
    caller_type: str | None = None,
):
    upactlog = UpdateActivityLog(ses=ses)
    init_subinfo = {
        "caller_type": caller_type,
        "start_utc_date": start_utc_date,
        "end_utc_date": end_utc_date,
    }
    if start_utc_date is None and end_utc_date is None:
        new_start_date = await get_new_start_date(upactivitylog=upactlog)
        if new_start_date:
            init_subinfo["new_start_utc_date"] = new_start_date
            start_utc_date = new_start_date
    db_taskactlog = await upactlog.create(
        target_id=str(uuid.uuid4()), activity_type=ACTIVITY_TYPE, subinfo=init_subinfo
    )
    taskactlog_id = db_taskactlog.id
    await upactlog.in_progress(id=taskactlog_id)

    urlnotirepo = n_repo.URLNotificationRepository(ses=ses)
    urlnoti_list = await urlnotirepo.get(
        command=noti_cmd.URLNotificationGetCommand(is_active=True)
    )
    url_id_list = [urlnoti.id for urlnoti in urlnoti_list]
    urlrepo = p_repo.URLRepository(ses=ses)
    pricelogrepo = p_repo.PriceLogRepository(ses=ses)
    target_results = {}
    err_msgs = []
    err_ids = []
    for url_id in url_id_list:
        db_activitylog = await upactlog.create(
            target_id=url_id,
            target_table="URL",
            activity_type=ACTIVITY_TYPE,
            range_type=act_enums.RangeType.TODAY.name,
            subinfo=init_subinfo,
        )
        activitylog_id = db_activitylog.id
        await upactlog.in_progress(id=activitylog_id)

        urlinfo = await urlrepo.get(command=p_cmd.URLGetCommand(id=url_id))
        if not urlinfo:
            errmsg = "URL is not found"
            await upactlog.canceled(id=activitylog_id, error_msg=errmsg)
            err_msgs.append("{" + f"{url_id}:{errmsg}" + "}")
            target_results[url_id] = {"error": f"{errmsg}"}
            continue
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
            err_msgs.append("{" + f"{url_id}:{errmsg}" + "}")
            target_results[url_id] = {"error": f"{errmsg}"}

            if log:
                log.warning("no length target_pricelogs, skip", url_id=url_id)
            continue
        target_results[url_id] = {
            "update_pricelog_ids": [p.id for p in target_pricelogs]
        }
        ok, msg = await send_to_api(ses=ses, pricelog_list=target_pricelogs)
        if ok:
            await upactlog.completed(
                id=activitylog_id, add_subinfo=target_results[url_id]
            )
            if log:
                log.info("send to api ... OK", url_id=url_id)
            continue

        await upactlog.failed(
            id=activitylog_id, error_msg=msg, add_subinfo=target_results[url_id]
        )
        err_msgs.append("{" + f"{url_id}:{msg}" + "}")
        target_results[url_id] |= {"error": f"{msg}"}
        err_ids.append(url_id)
        if log:
            log.error("send to api ... NG", url_id=url_id, error_msg=msg)
        continue

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
