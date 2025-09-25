import asyncio
from urllib.parse import urlparse
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from domain.models.notification import command as noti_cmd
from domain.models.pricelog import command as p_cmd
from databases.sql import util as db_util
from databases.sql.pricelog import repository as p_repo
from databases.sql.notification import repository as n_repo
from app.sofmap import web_scraper as sofmap_scraper
from app.geo import web_scraper as geo_scraper
from app.iosys import web_scraper as iosys_scraper
from app.gemini import web_scraper as gemini_scraper
from common import read_config
from app.activitylog.update import UpdateActivityLog
from app.activitylog.util import is_updating_urls_or_sending_to_api
from . import constants as update_const
from app.getdata.models import search as search_models
from app.enums import SiteName, SupportDomain


async def _scrape_one_url(url_id: int, urlopts: read_config.UpdateURLOptions, log=None):
    async for ses in db_util.get_async_session():
        urlrepo = p_repo.URLRepository(ses=ses)
        urloptrepo = n_repo.URLUpdateParameterRepository(ses=ses)
        target_url = await urlrepo.get(command=p_cmd.URLGetCommand(id=url_id))
        if not target_url:
            if log:
                log.warning("URL not found", url_id=url_id)
            return {"url_id": url_id, "ok": False, "msg": "URL not found"}
        target_url_str = target_url.url
        parsed_url = urlparse(target_url_str)
        if not parsed_url.scheme or not parsed_url.netloc:
            if log:
                log.error("Invalid URL", url=target_url_str)
            return {"url_id": url_id, "ok": False, "msg": "Invalid URL"}

        ok = False
        result = ""
        try:
            match parsed_url.netloc:
                case SupportDomain.SOFMAP.value | SupportDomain.A_SOFMAP.value:
                    searchreq = search_models.SearchRequest(
                        url=target_url_str,
                        search_keyword=None,
                        sitename=SiteName.SOFMAP.value,
                        options=urlopts.request_options.model_dump(exclude_none=True),
                    )
                    ok, result = await sofmap_scraper.download_with_api(
                        ses=ses, searchreq=searchreq, save_to_db=True
                    )
                case SupportDomain.GEO.value:
                    searchreq = search_models.SearchRequest(
                        url=target_url_str,
                        search_keyword=None,
                        sitename=SiteName.GEO.value,
                        options=urlopts.request_options.model_dump(exclude_none=True),
                    )
                    ok, result = await geo_scraper.download_with_api(
                        ses=ses, searchreq=searchreq, save_to_db=True
                    )
                case SupportDomain.IOSYS.value:
                    searchreq = search_models.SearchRequest(
                        url=target_url_str,
                        search_keyword=None,
                        sitename=SiteName.IOSYS.value,
                        options=urlopts.request_options.model_dump(exclude_none=True),
                    )
                    ok, result = await iosys_scraper.download_with_api(
                        ses=ses, searchreq=searchreq, save_to_db=True
                    )
                case _:
                    db_urlopt = await urloptrepo.get(
                        command=noti_cmd.URLUpdateParameterGetCommand(url_id=url_id)
                    )
                    if not db_urlopt or db_urlopt[0].sitename != SiteName.GEMINI.value:
                        msg = f"Unsupported netloc: {parsed_url.netloc}"
                        if log:
                            log.error(
                                "Unsupported netloc",
                                url=target_url.url,
                                netloc=parsed_url.netloc,
                            )
                        return {"url_id": url_id, "ok": False, "msg": msg}

                    searchreq = search_models.SearchRequest(
                        url=target_url_str,
                        search_keyword="",
                        sitename=SiteName.GEMINI.value,
                        options=db_urlopt[0].meta,
                    )
                    ok, result = await gemini_scraper.download_with_api(
                        ses=ses, searchreq=searchreq, save_to_db=True
                    )
        except Exception as e:
            if log:
                log.error(f"Scraping failed for {target_url_str} with error: {e}")
            return {"url_id": url_id, "ok": False, "msg": str(e)}

        if ok:
            await ses.refresh(target_url)
            target_id = target_url.id
            if log:
                log.info("update and save ... ok", url=target_url_str)
            await asyncio.sleep(update_const.OK_WAIT_TIME)
            return {"url_id": target_id, "ok": True, "msg": ""}

        msg = result
        if log:
            log.error("update and save ... ng", url=target_url_str, error_msg=msg)
        await ses.refresh(target_url)
        target_id = target_url.id
        await asyncio.sleep(update_const.NG_WAIT_TIME)
        return {"url_id": target_id, "ok": False, "msg": msg}


async def scraping_and_save_target_urls(
    ses: AsyncSession, log=None, caller_type: str = None, url_id: int = None
):
    up_activitylog = UpdateActivityLog(ses=ses)
    if await is_updating_urls_or_sending_to_api(updateactlog=up_activitylog):
        msg = "cancelled due to updating urls or sending to api."
        if log:
            log.warning(msg)
        return

    db_activitylog = await up_activitylog.create(
        target_id=str(uuid.uuid4()),
        activity_type=update_const.SCRAPING_URL_ACTIVITY_TYPE,
        caller_type=caller_type,
    )
    activitylog_id = db_activitylog.id
    await up_activitylog.in_progress(id=activitylog_id)

    urlnotirepo = n_repo.URLNotificationRepository(ses=ses)

    command = noti_cmd.URLNotificationGetCommand(is_active=True)
    if url_id:
        command.url_id = url_id

    target_urlnotis = await urlnotirepo.get(command=command)
    if not target_urlnotis:
        msg = "No target urls"
        if url_id:
            msg = f"No active target url for url_id: {url_id}"
        await up_activitylog.canceled(id=activitylog_id, error_msg=msg)
        if log:
            log.warning(msg)
        return

    target_url_ids = [urlnoti.url_id for urlnoti in target_urlnotis]
    urlopts = read_config.get_update_url_options()
    tasks = [
        _scrape_one_url(url_id, urlopts=urlopts, log=log) for url_id in target_url_ids
    ]
    if urlopts.excution_strategy == "sequential":
        results = []
        for task in tasks:
            results.append(await task)
    else:  # parallel
        results = await asyncio.gather(*tasks)

    target_results = {}
    err_msgs = []
    err_ids = []
    for res in results:
        url_id = res["url_id"]
        target_results[url_id] = {}
        if not res["ok"]:
            msg = res["msg"]
            target_results[url_id] = {"error": f"{msg}"}
            err_msgs.append("{" + f"{url_id}:{msg}" + "}")
            err_ids.append(url_id)

    add_subinfo = {"target_results": target_results}
    if not err_msgs:
        await up_activitylog.completed(id=activitylog_id, add_subinfo=add_subinfo)
        return
    elif len(err_ids) == len(target_url_ids):
        await up_activitylog.failed(
            id=activitylog_id, error_msg=",".join(err_msgs), add_subinfo=add_subinfo
        )
        return
    else:
        await up_activitylog.completed_with_error(
            id=activitylog_id, error_msg=",".join(err_msgs), add_subinfo=add_subinfo
        )
        return
