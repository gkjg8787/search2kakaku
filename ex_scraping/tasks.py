import asyncio

from celery import Celery
from celery.schedules import crontab

from databases.sqldb import util as db_util
from app.update import scraping_urls
from app.notification import to_api


app = Celery(
    "auto_updates", broker="redis://redis:6379/0", backend="redis://redis:6379/0"
)

app.conf.beat_schedule = {
    # "update-and-notify-every-day": {
    #    "task": "tasks.update_urls_and_notify_to_api",
    #    "schedule": crontab(hour="14"),
    # },
    "update-every-day": {
        "task": "tasks.update_urls",
        "schedule": crontab(hour="14"),
    }
}
app.conf.timezone = "Asia/Tokyo"  # タイムゾーンの設定

CALLER_TYPE = "celery"


async def a_update_urls():
    async for ses in db_util.get_async_session():
        await scraping_urls.scraping_and_save_target_urls(
            ses=ses, caller_type=CALLER_TYPE
        )


async def a_update_urls_and_notify_to_api():
    async for ses in db_util.get_async_session():
        await scraping_urls.scraping_and_save_target_urls(
            ses=ses, caller_type=CALLER_TYPE
        )
        await to_api.send_target_URLs_to_api(
            ses=ses, start_utc_date=None, end_utc_date=None, caller_type=CALLER_TYPE
        )


@app.task
def update_urls():
    asyncio.run(a_update_urls())
    return


@app.task
def update_urls_and_notify_to_api():
    asyncio.run(a_update_urls_and_notify_to_api())
