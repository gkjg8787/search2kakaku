import asyncio
import argparse
import uuid

import structlog

from common import logger_config
from domain.models.activitylog import activitylog
from domain.models.pricelog import pricelog
from domain.models.notification import notification
from databases.sql import util as db_util
from app.update import scraping_urls

CALLER_TYPE = "user"


def set_argparse():
    parser = argparse.ArgumentParser(
        description="アップデート対象のURLを取得しログに登録します。"
    )
    parser.add_argument("--url_id", type=int, help="単一のurl_idを指定する")
    return parser.parse_args()


async def main():
    logger_config.configure_logger()
    run_id = str(uuid.uuid4())
    log = structlog.get_logger(__name__).bind(run_id=run_id, process_type="update_urls")

    argp = set_argparse()

    db_util.create_db_and_tables()
    async for ses in db_util.get_async_session():
        await scraping_urls.scraping_and_save_target_urls(
            ses=ses, log=log, caller_type=CALLER_TYPE, url_id=argp.url_id
        )


if __name__ == "__main__":
    asyncio.run(main())