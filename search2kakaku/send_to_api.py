import asyncio
import argparse
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import uuid
from enum import auto
import re

import structlog

from common import logger_config, enums
from domain.models.activitylog import activitylog
from domain.models.pricelog import pricelog
from domain.models.notification import notification
from databases.sql import util as db_util
from app.notification import send_pricelog, create_item, add_urls, get_items


DATETIME_FORMAT = "%Y/%m/%d %H:%M:%S"
JST = ZoneInfo("Asia/Tokyo")
CALLER_TYPE = "user"


class CommandOrder(enums.AutoLowerName):
    SEND_LOG = auto()
    CREATE_ITEM = auto()
    ADD_URL = auto()
    GET_ITEM = auto()


def set_argparse():
    parser = argparse.ArgumentParser(
        description="APIを通して操作します。APIへのログの送信、アイテムの新規作成、既存アイテムへのURL登録を行います。"
    )
    subparsers = parser.add_subparsers(
        dest="command", help="利用可能なコマンド", required=True
    )

    send_log_parser = subparsers.add_parser(
        CommandOrder.SEND_LOG.value,
        help="ログをAPIへ転送します。対象ログの範囲の開始日時を指定しない場合、最近の通知履歴の更新時間+マイクロ秒を対象を開始時刻として利用します。",
    )
    start_date_group = send_log_parser.add_mutually_exclusive_group(required=False)
    start_date_group.add_argument(
        "-sud",
        "--start_utc_date",
        type=lambda d: datetime.strptime(d, DATETIME_FORMAT).replace(
            tzinfo=timezone.utc
        ),
        help=f'通知するログデータ範囲の開始日時(UTC): "yyyy/mm/dd HH:MM:SS"のフォーマットで指定',
    )
    start_date_group.add_argument(
        "-sjd",
        "--start_jst_date",
        type=lambda d: datetime.strptime(d, DATETIME_FORMAT).replace(tzinfo=JST),
        help=f'通知するログデータ範囲の開始日時(JST): "yyyy/mm/dd HH:MM:SS"のフォーマットで指定',
    )
    end_date_group = send_log_parser.add_mutually_exclusive_group(required=False)
    end_date_group.add_argument(
        "-eud",
        "--end_utc_date",
        type=lambda d: datetime.strptime(d, DATETIME_FORMAT).replace(
            tzinfo=timezone.utc
        ),
        help=f'通知するログデータ範囲の終了日時(UTC): "yyyy/mm/dd HH:MM:SS"のフォーマットで指定',
    )
    end_date_group.add_argument(
        "-ejd",
        "--end_jst_date",
        type=lambda d: datetime.strptime(d, DATETIME_FORMAT).replace(tzinfo=JST),
        help=f'通知するログデータ範囲の終了日時(JST): "yyyy/mm/dd HH:MM:SS"のフォーマットで指定',
    )

    create_item_parser = subparsers.add_parser(
        CommandOrder.CREATE_ITEM.value,
        help="新規にアイテムを作成します。",
    )
    create_item_parser.add_argument(
        "--name", help="新規に追加するアイテム名。", required=True
    )
    create_item_parser.add_argument(
        "--url",
        nargs="+",
        help="アイテムに追加 or 情報を表示する 対象のURL文字列。複数の場合 'url1' 'url2' と指定する。",
        required=True,
    )

    add_url_to_item_parser = subparsers.add_parser(
        CommandOrder.ADD_URL.value,
        help="既存のアイテムにURLを追加します。",
    )
    add_url_to_item_parser.add_argument(
        "--item_id",
        type=int,
        help="URLを追加するアイテムID。事前に登録済みであることが必要です。",
        required=True,
    )
    add_url_to_item_parser.add_argument(
        "--url",
        nargs="+",
        help="アイテムに追加 or 情報を表示する 対象のURL文字列。複数の場合 'url1' 'url2' と指定する。",
        required=True,
    )

    get_item_parser = subparsers.add_parser(
        CommandOrder.GET_ITEM.value,
        help="指定したURLから関連のアイテム一覧を取得します。",
    )
    get_item_parser.add_argument(
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


def is_valid_urls(urls: str) -> tuple[bool, str]:
    for url in urls:
        if not is_valid_url(url):
            return False, url
    return True, ""


async def send_log_to_api(argp, log):
    if not argp.start_jst_date and not argp.start_utc_date:
        start_utc_date = None
    elif argp.start_jst_date:
        start_utc_date = argp.start_jst_date.astimezone(timezone.utc)
    elif argp.start_utc_date:
        start_utc_date = argp.start_utc_date
    else:
        start_utc_date = None

    if not argp.end_jst_date and not argp.end_utc_date:
        end_utc_date = None
    elif argp.end_jst_date:
        end_utc_date = argp.end_jst_date.astimezone(timezone.utc)
    elif argp.end_utc_date:
        end_utc_date = argp.end_utc_date
    else:
        end_utc_date = None

    async for ses in db_util.get_async_session():
        await send_pricelog.send_target_URLs_to_api(
            ses=ses,
            start_utc_date=start_utc_date,
            end_utc_date=end_utc_date,
            log=log,
            caller_type=CALLER_TYPE,
        )


async def main():
    logger_config.configure_logger()
    run_id = str(uuid.uuid4())
    log = structlog.get_logger(__name__).bind(run_id=run_id, process_type="send_to_api")

    argp = set_argparse()
    log.info("get parameters ...", **vars(argp))
    db_util.create_db_and_tables()
    if argp.command == CommandOrder.SEND_LOG.value:
        await send_log_to_api(argp=argp, log=log)
        return

    # CommandOrder.CREATE_ITEM, CommandOrder.ADD_URL, CommandOrder.GET_ITEM
    ok, msg = is_valid_urls(urls=argp.url)
    if not ok:
        log.error("invalid URL", url=msg)
        return

    async for ses in db_util.get_async_session():
        if argp.command == CommandOrder.CREATE_ITEM.value:
            await create_item.create_item_with_api(
                ses=ses,
                item_name=argp.name,
                urls=argp.url,
                log=log,
                caller_type=CALLER_TYPE,
            )
            return
        if argp.command == CommandOrder.ADD_URL.value:
            await add_urls.add_urls_to_item_with_api(
                ses=ses,
                item_id=argp.item_id,
                urls=argp.url,
                log=log,
                caller_type=CALLER_TYPE,
            )
            return
        if argp.command == CommandOrder.GET_ITEM.value:
            await get_items.get_items_by_url_with_api(
                ses=ses, urls=argp.url, log=log, caller_type=CALLER_TYPE
            )
            return


if __name__ == "__main__":
    asyncio.run(main())
