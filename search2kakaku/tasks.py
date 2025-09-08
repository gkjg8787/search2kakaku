import asyncio

from celery import Celery
from celery.schedules import crontab

from databases.sql import util as db_util
from app.update import scraping_urls
from app.notification import send_pricelog
from common import read_config

redisoptions = read_config.get_redis_options()
redis_url = f"redis://{redisoptions.host}:{redisoptions.port}/{redisoptions.db}"
app = Celery("auto_updates", broker=redis_url, backend=redis_url)

autoupdate_opts = read_config.get_auto_update_options()

app.conf.beat_schedule = {
    "update-and-notify-every-day": {
        "task": "tasks.update_urls_and_notify_to_api",
        "schedule": crontab(**autoupdate_opts.schedule),
        "options": {
            "expires": 10,  # 有効期限を秒で指定
        },
    },
}
app.conf.timezone = "Asia/Tokyo"  # タイムゾーンの設定

CALLER_TYPE = "celery"


async def a_update_urls_and_notify_to_api():
    async for ses in db_util.get_async_session():
        await scraping_urls.scraping_and_save_target_urls(
            ses=ses, caller_type=CALLER_TYPE
        )
        if not autoupdate_opts.notify_to_api:
            return
        await send_pricelog.send_target_URLs_to_api(
            ses=ses, start_utc_date=None, end_utc_date=None, caller_type=CALLER_TYPE
        )


@app.task
def update_urls_and_notify_to_api():
    if not autoupdate_opts.enable:
        return
    asyncio.run(a_update_urls_and_notify_to_api())
