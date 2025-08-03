import asyncio
import argparse
import uuid
import re

import structlog

from common import logger_config
from domain.models.activitylog import activitylog
from domain.models.pricelog import pricelog
from domain.models.notification import notification
from databases.sqldb import util as db_util
from app.notification import create_item, add_urls, get_items

CALLER_TYPE = "user"


def set_argparse():
    parser = argparse.ArgumentParser(
        description="APIを通してアイテムの作成とURLの追加を行います。既に追加済みの場合は新たに追加しません。"
    )
    order_type_group = parser.add_mutually_exclusive_group(required=True)
    order_type_group.add_argument(
        "--new_item",
        type=str,
        help="新規に追加するアイテム名。API先に同じ名前が存在していても新規に追加します。",
    )
    order_type_group.add_argument(
        "--item_id",
        type=int,
        help="URLを追加するアイテムID。事前に登録済みであることが必要です。",
    )
    order_type_group.add_argument(
        "--get_item",
        action="store_true",
        help="登録済みのURLと関係するアイテム情報の取得。",
    )
    parser.add_argument(
        "--url",
        nargs="+",
        help="アイテムに追加 or 情報を表示する 対象のURL文字列。複数の場合 'url1' 'url2' と指定する。",
        required=True,
    )
    return parser.parse_args()


def is_valid_url(url: str) -> bool:
    url_pattern = re.compile(
        r"^(?:http|ftp)s?://"  # http:// or https:// or ftp:// or ftps://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # domain...
        r"localhost|"  # localhost...
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )
    if not url:
        return False

    return re.match(url_pattern, url) is not None


async def main():
    logger_config.configure_logger()
    run_id = str(uuid.uuid4())
    log = structlog.get_logger(__name__).bind(
        run_id=run_id, process_type="create_item_url_via_api.py"
    )

    argp = set_argparse()
    for url in argp.url:
        if not is_valid_url(url):
            log.error("invalid URL", url=url)
            return
    log.info("get parameters ...", **vars(argp))

    db_util.create_db_and_tables()
    async for ses in db_util.get_async_session():
        if argp.new_item:
            await create_item.create_item_with_api(
                ses=ses,
                item_name=argp.new_item,
                urls=argp.url,
                log=log,
                caller_type=CALLER_TYPE,
            )
            return
        if argp.item_id:
            await add_urls.add_urls_to_item_with_api(
                ses=ses,
                item_id=argp.item_id,
                urls=argp.url,
                log=log,
                caller_type=CALLER_TYPE,
            )
            return
        if argp.get_item:
            await get_items.get_items_by_url_with_api(
                ses=ses, urls=argp.url, log=log, caller_type=CALLER_TYPE
            )
            return


if __name__ == "__main__":
    asyncio.run(main())
