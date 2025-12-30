from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from databases.sql.util import get_async_session
from databases.sql.activitylog import repository as log_repo
from domain.models.activitylog import command as log_cmd
from domain.models.activitylog import activitylog as m_actlog
from databases.sql.pricelog import repository as pl_repo
from domain.models.pricelog import command as pl_cmd
from domain.models.pricelog import pricelog as m_pricelog

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/activity", response_model=list[m_actlog.ActivityLog])
async def get_logs(
    db: AsyncSession = Depends(get_async_session),
    limit: int = Query(default=100),
    is_error: bool | None = Query(default=None),
    activity_type: str | None = Query(default=None),
    caller_type: str | None = Query(default=None),
):
    repo = log_repo.ActivityLogRepository(db)
    cmd = log_cmd.ActivityLogGetCommand(
        limit=limit,
        is_error=is_error,
        activity_types=[activity_type] if activity_type else [],
        caller_type=caller_type,
    )
    return await repo.get(cmd)


@router.get("/activity/filters")
async def get_filters(
    db: AsyncSession = Depends(get_async_session),
):
    repo = log_repo.ActivityLogRepository(db)
    return {
        "activity_types": await repo.get_activity_types(),
        "caller_types": await repo.get_caller_types(),
    }


@router.get("/price", response_model=list[m_pricelog.PriceLog])
async def get_pricelogs(
    db: AsyncSession = Depends(get_async_session),
    limit: int = Query(default=100),
    title: str | None = Query(default=None),
    condition: str | None = Query(default=None),
    url: str | None = Query(default=None),
):
    repo = pl_repo.PriceLogRepository(db)
    cmd = pl_cmd.PriceLogGetCommand()
    return await repo.get(
        cmd, limit=limit, title=title, condition=condition, url_filter=url
    )
