import sys
import asyncio
import argparse
from datetime import datetime, timezone, time
from zoneinfo import ZoneInfo

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

    parser.add_argument(
        "-sut",
        "--start_utc_time",
        type=lambda d: datetime.strptime(d, DATETIME_FORMAT).replace(
            tzinfo=timezone.utc
        ),
        help=f'通知するログデータ範囲の開始日時(UTC): "yyyy/mm/dd HH:MM:SS"のフォーマットで指定',
    )
    parser.add_argument(
        "-sjt",
        "--start_jst_time",
        type=lambda d: datetime.strptime(d, DATETIME_FORMAT).replace(tzinfo=JST),
        help=f'通知するログデータ範囲の開始日時(JST): "yyyy/mm/dd HH:MM:SS"のフォーマットで指定',
    )
    return parser.parse_args(argv)


def get_start_date(rangetype: n_enums.RangeType) -> datetime | None:
    if rangetype == n_enums.RangeType.TODAY:
        return datetime.combine(datetime.today(), time.min, tzinfo=timezone.utc)
    return None


async def main(argv):
    argp = set_argparse(argv[1:])
    if not argp.start_jst_time or not argp.start_utc_time:
        start_utc_date = get_start_date(n_enums.RangeType.TODAY)
    elif argp.start_jst_time:
        start_utc_date = argp.start_jst_time.astimezone(timezone.utc)
    elif argp.sstart_utc_timeut:
        start_utc_date = argp.start_utc_time
    else:
        start_utc_date = None

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
                    url=urlinfo.url, start_utc_date=start_utc_date
                )
            )
            if not target_pricelogs:
                print(f"no length target_pricelogs, skip, url_id:{urlnoti.url_id}")
                continue
            ok, msg = await to_api.send_to_api(ses=ses, pricelog_list=target_pricelogs)
            if ok:
                print(f"url_id:{urlnoti.url_id} send to api ... OK")
            else:
                print(f"url_id:{urlnoti.url_id} send to api ... NG, {msg}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv))
