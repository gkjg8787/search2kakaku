import sys
import asyncio
import argparse
from datetime import datetime, timezone, time
from zoneinfo import ZoneInfo
import uuid

import structlog

from common import logger_config
from domain.models.notification import command as noti_cmd, enums as n_enums
from domain.models.pricelog import command as p_cmd
from databases.sqldb.pricelog import repository as p_repo
from databases.sqldb.notification import repository as n_repo
from databases.sqldb import util as db_util
from app.notification import to_api

DATETIME_FORMAT = "%Y/%m/%d %H:%M:%S"
JST = ZoneInfo("Asia/Tokyo")


def set_argparse(argv):
    parser = argparse.ArgumentParser(description="ログをAPIへ転送します。")
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
    return parser.parse_args(argv)


def get_start_date(rangetype: n_enums.RangeType) -> datetime | None:
    if rangetype == n_enums.RangeType.TODAY:
        return datetime.combine(datetime.today(), time.min, tzinfo=timezone.utc)
    return None


async def main(argv):
    logger_config.configure_logger()
    run_id = str(uuid.uuid4())
    log = structlog.get_logger(__name__).bind(
        run_id=run_id, process_type="notify_to_api"
    )

    argp = set_argparse(argv[1:])
    if not argp.start_jst_date or not argp.start_utc_date:
        start_utc_date = get_start_date(n_enums.RangeType.TODAY)
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

    async for ses in db_util.get_async_session():
        urlnotirepo = n_repo.URLNotificationRepository(ses=ses)
        urlnoti_list = await urlnotirepo.get(
            command=noti_cmd.URLNotificationGetCommand(is_active=True)
        )
        urlrepo = p_repo.URLRepository(ses=ses)
        pricelogrepo = p_repo.PriceLogRepository(ses=ses)
        for urlnoti in urlnoti_list:
            urlinfo = await urlrepo.get(command=p_cmd.URLGetCommand(id=urlnoti.url_id))
            if not urlinfo:
                continue
            target_pricelogs = await pricelogrepo.get(
                command=p_cmd.PriceLogGetCommand(
                    url=urlinfo.url,
                    start_utc_date=start_utc_date,
                    end_utc_date=end_utc_date,
                )
            )
            if not target_pricelogs:
                log.warning("no length target_pricelogs, skip", url_id=urlnoti.url_id)
                continue
            ok, msg = await to_api.send_to_api(ses=ses, pricelog_list=target_pricelogs)
            if ok:
                log.info("send to api ... OK", url_id=urlnoti.url_id)
            else:
                log.error("send to api ... NG", url_id=urlnoti.url_id, error_msg=msg)


if __name__ == "__main__":
    asyncio.run(main(sys.argv))
