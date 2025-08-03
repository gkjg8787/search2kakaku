import asyncio
import argparse
from datetime import datetime, timezone, time
from zoneinfo import ZoneInfo
import uuid

import structlog

from common import logger_config
from domain.models.notification import command as noti_cmd
from domain.models.pricelog import command as p_cmd
from domain.models.activitylog import activitylog
from databases.sqldb.pricelog import repository as p_repo
from databases.sqldb.notification import repository as n_repo
from databases.sqldb import util as db_util
from app.notification import send_pricelog

DATETIME_FORMAT = "%Y/%m/%d %H:%M:%S"
JST = ZoneInfo("Asia/Tokyo")
CALLER_TYPE = "user"


def set_argparse():
    parser = argparse.ArgumentParser(
        description="ログをAPIへ転送します。対象ログの範囲の開始日時を指定しない場合、最近の通知履歴の更新時間+マイクロ秒を対象を開始時刻として利用します。"
    )
    start_date_group = parser.add_mutually_exclusive_group(required=False)
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
    end_date_group = parser.add_mutually_exclusive_group(required=False)
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
    return parser.parse_args()


async def main():
    logger_config.configure_logger()
    run_id = str(uuid.uuid4())
    log = structlog.get_logger(__name__).bind(
        run_id=run_id, process_type="notify_to_api"
    )

    argp = set_argparse()
    if not argp.start_jst_date or not argp.start_utc_date:
        start_utc_date = None
    elif argp.start_jst_date:
        start_utc_date = argp.start_jst_date.astimezone(timezone.utc)
    elif argp.start_utc_date:
        start_utc_date = argp.start_utc_date
    else:
        start_utc_date = None

    if not argp.end_jst_date or not argp.end_utc_date:
        end_utc_date = None
    elif argp.end_jst_date:
        end_utc_date = argp.end_jst_date.astimezone(timezone.utc)
    elif argp.end_utc_date:
        end_utc_date = argp.end_utc_date
    else:
        end_utc_date = None

    db_util.create_db_and_tables()
    async for ses in db_util.get_async_session():
        await send_pricelog.send_target_URLs_to_api(
            ses=ses,
            start_utc_date=start_utc_date,
            end_utc_date=end_utc_date,
            log=log,
            caller_type=CALLER_TYPE,
        )


if __name__ == "__main__":
    asyncio.run(main())
