import asyncio
from urllib.parse import urlparse
from enum import Enum, auto
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from domain.models.notification import command as noti_cmd
from domain.models.pricelog import command as p_cmd
from databases.sqldb.pricelog import repository as p_repo
from databases.sqldb.notification import repository as n_repo
from app.sofmap import web_scraper, constants as sofmap_contains
from common import read_config
from .update_activitylog import UpdateActivityLog

OK_WAIT_TIME = 2
NG_WAIT_TIME = 4

SCRAPING_AND_SAVE = "SCRAPING_AND_SAVE"


def is_a_sofmap(url: str):
    parsedurl = urlparse(url)
    return parsedurl.netloc == sofmap_contains.A_SOFMAP_NETLOC


async def scraping_and_save_target_urls(
    ses: AsyncSession, log=None, caller_type: str = None
):
    up_activitylog = UpdateActivityLog(ses=ses)
    db_activitylog = await up_activitylog.create(
        target_id=str(uuid.uuid4()),
        activity_type=SCRAPING_AND_SAVE,
        subinfo={"caller_type": caller_type},
    )
    activitylog_id = db_activitylog.id
    await up_activitylog.in_progress(id=activitylog_id)

    urlnotirepo = n_repo.URLNotificationRepository(ses=ses)
    target_urlnotis = await urlnotirepo.get(
        command=noti_cmd.URLNotificationGetCommand(is_active=True)
    )
    if not target_urlnotis:
        msg = "No target urls"
        await up_activitylog.canceled(id=activitylog_id, error_msg=msg)
        if log:
            log.warning(msg)
        return
    target_url_ids = [urlnoti.id for urlnoti in target_urlnotis]
    urlrepo = p_repo.URLRepository(ses=ses)
    sofmapopts = read_config.get_sofmap_options()
    seleniumopts = read_config.get_selenium_options()
    target_results = {}
    err_msgs = []
    err_ids = []
    for url_id in target_url_ids:
        target_url = await urlrepo.get(command=p_cmd.URLGetCommand(id=url_id))
        if not target_url:
            target_results[url_id] = {"error": "URL not found"}
            if log:
                log.warning("URL not found", url_id=url_id)
            continue
        command = web_scraper.ScrapeCommand(
            url=target_url.url,
            async_session=ses,
            is_ucaa=is_a_sofmap(target_url.url),
            selenium_url=seleniumopts.remote_url,
            page_load_timeout=sofmapopts.selenium.page_load_timeout,
            tag_wait_timeout=sofmapopts.selenium.tag_wait_timeout,
        )
        ok, msg = await web_scraper.scrape_and_save(command=command)
        await ses.refresh(target_url)
        if ok:
            target_results[target_url.id] = {}
            if log:
                log.info("update and save ... ok", url=target_url.url)
            await asyncio.sleep(OK_WAIT_TIME)
            continue
        target_results[target_url.id] = {"error": f"{msg}"}
        err_msgs.append("{" + f"{target_url.id}:{msg}" + "}")
        err_ids.append(target_url.id)
        if log:
            log.error("update and save ... ng", url=target_url.url, error_msg=msg)
        await asyncio.sleep(NG_WAIT_TIME)
        continue

    add_subinfo = {"target_results": target_results}
    if not err_msgs:
        await up_activitylog.completed(id=activitylog_id, add_subinfo=add_subinfo)
    elif len(err_ids) == len(target_url_ids):
        await up_activitylog.failed(
            id=activitylog_id, error_msg=",".join(err_msgs), add_subinfo=add_subinfo
        )
    else:
        await up_activitylog.completed_with_error(
            id=activitylog_id, error_msg=",".join(err_msgs), add_subinfo=add_subinfo
        )
