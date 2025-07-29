import sys
import asyncio
import argparse
from urllib.parse import urlparse
import uuid

import structlog

from common import logger_config
from domain.models.notification import command as noti_cmd
from domain.models.pricelog import command as p_cmd
from databases.sqldb.pricelog import repository as p_repo
from databases.sqldb.notification import repository as n_repo
from databases.sqldb import util as db_util
from app.sofmap import web_scraper, constants as sofmap_contains
from common import read_config


def set_argparse(argv):
    parser = argparse.ArgumentParser(
        description="アップデート対象のURLを取得しログに登録します。"
    )
    return parser.parse_args(argv)


def is_a_sofmap(url: str):
    parsedurl = urlparse(url)
    return parsedurl.netloc == sofmap_contains.A_SOFMAP_NETLOC


async def main(argv):
    logger_config.configure_logger()
    run_id = str(uuid.uuid4())
    log = structlog.get_logger(__name__).bind(run_id=run_id, process_type="update_urls")

    argp = set_argparse(argv[1:])
    async for ses in db_util.get_async_session():
        urlnotirepo = n_repo.URLNotificationRepository(ses=ses)
        target_urlnotis = await urlnotirepo.get(
            command=noti_cmd.URLNotificationGetCommand(is_active=True)
        )
        if not target_urlnotis:
            log.error("No target urls")
            return
        urlrepo = p_repo.URLRepository(ses=ses)
        sofmapopts = read_config.get_sofmap_options()
        seleniumopts = read_config.get_selenium_options()
        for urlnoti in target_urlnotis:
            target_url = await urlrepo.get(
                command=p_cmd.URLGetCommand(id=urlnoti.url_id)
            )
            if not target_url:
                log.warning("target_url not found", url_id=urlnoti.url_id)
                continue
            command = web_scraper.ScrapeCommand(
                url=target_url,
                async_session=ses,
                is_ucaa=is_a_sofmap(target_url),
                selenium_url=seleniumopts.remote_url,
                page_load_timeout=sofmapopts.selenium.page_load_timeout,
                tag_wait_timeout=sofmapopts.selenium.tag_wait_timeout,
            )
            ok, msg = await web_scraper.scrape_and_save(command=command)
            if ok:
                log.info("update and save ... ok", url=target_url)
                continue
            log.error("update and save ... ng", url=target_url, error_msg=msg)


if __name__ == "__main__":
    asyncio.run(main(sys.argv))
