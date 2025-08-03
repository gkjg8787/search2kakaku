from domain.models.activitylog import command as act_cmd
from .update import UpdateActivityLog


async def get_activitylog_latest(upactivitylog: UpdateActivityLog, activity_type: str):
    db_actlogs = await upactivitylog.get_all(
        command=act_cmd.ActivityLogGetCommand(activity_type=activity_type)
    )
    if not db_actlogs:
        return None
    lastest_actlog = max(db_actlogs, key=lambda log: log.updated_at)
    return lastest_actlog
