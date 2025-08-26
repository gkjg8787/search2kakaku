from domain.models.activitylog import command as act_cmd, enums as act_enums
from .update import UpdateActivityLog
from app.update import constants as update_const
from app.notification import constants as noti_const


async def get_activitylog_latest(
    upactivitylog: UpdateActivityLog,
    activity_types: list[str],
    current_states: list[str] | None = [
        act_enums.UpdateStatus.COMPLETED.name,
        act_enums.UpdateStatus.COMPLETED_WITH_ERRORS.name,
    ],
):
    db_actlogs = await upactivitylog.get_all(
        command=act_cmd.ActivityLogGetCommand(
            activity_types=activity_types,
            current_states=current_states,
        )
    )
    if not db_actlogs:
        return None
    lastest_actlog = max(db_actlogs, key=lambda log: log.updated_at)
    return lastest_actlog


async def is_updating_urls_or_sending_to_api(updateactlog: UpdateActivityLog):
    db_actlog = await get_activitylog_latest(
        upactivitylog=updateactlog,
        activity_types=[
            update_const.SCRAPING_URL_ACTIVITY_TYPE,
            noti_const.SEND_LOG_ACTIVITY_TYPE,
        ],
        current_states=[act_enums.UpdateStatus.IN_PROGRESS.name],
    )
    if not db_actlog:
        return False
    return True
