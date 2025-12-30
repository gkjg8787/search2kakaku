import uuid
from datetime import datetime

from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from databases.sql.util import get_async_session
from common import read_template
from databases.sql.activitylog import repository as log_repo
from domain.models.activitylog import command as log_cmd
from databases.sql.pricelog import repository as pl_repo
from domain.models.pricelog import command as pl_cmd

router = APIRouter(prefix="/log", tags=["view_logs"])
templates = read_template.templates
CALLER_TYPE = "html.log"


@router.get("/activity", response_class=HTMLResponse, name="log_list")
async def view_activitylogs(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    limit: int = Query(default=100),
    activity_type: str | None = Query(default=None),
    caller_type: str | None = Query(default=None),
    is_error: str = Query(default="all"),  # all, error, no_error
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
):
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        router_path=request.url.path,
        request_id=str(uuid.uuid4()),
        caller=CALLER_TYPE,
    )

    # Date handling
    now = datetime.now()
    if not start_date:
        dt_start = datetime(now.year, now.month, now.day)
        start_date_val = dt_start.strftime("%Y-%m-%d")
    else:
        dt_start = datetime.strptime(start_date, "%Y-%m-%d")
        start_date_val = start_date

    dt_end = None
    if end_date:
        # Set to end of the day
        dt_end = datetime.strptime(end_date, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59, microsecond=999999
        )

    # Error filter handling
    bool_is_error = None
    if is_error == "error":
        bool_is_error = True
    elif is_error == "no_error":
        bool_is_error = False

    repo = log_repo.ActivityLogRepository(db)

    cmd = log_cmd.ActivityLogGetCommand(
        limit=limit,
        activity_types=[activity_type] if activity_type else [],
        caller_type=caller_type,
        is_error=bool_is_error,
        updated_at_start=dt_start,
        updated_at_end=dt_end,
    )
    logs = await repo.get(cmd)

    # Fetch options for dropdowns
    act_types = await repo.get_activity_types()
    call_types = await repo.get_caller_types()

    context = {
        "logs": logs,
        "filters": {
            "limit": limit,
            "activity_type": activity_type,
            "caller_type": caller_type,
            "is_error": is_error,
            "start_date": start_date_val,
            "end_date": end_date or "",
        },
        "options": {"activity_types": act_types, "caller_types": call_types},
    }
    return templates.TemplateResponse(
        request=request, name="activitylog_list.html", context=context
    )


@router.get("/price", response_class=HTMLResponse, name="pricelog_list")
async def view_pricelogs(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    limit: int = Query(default=100),
    title: str | None = Query(default=None),
    condition: str | None = Query(default=None),
    url: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
):
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        router_path=request.url.path,
        request_id=str(uuid.uuid4()),
        caller=CALLER_TYPE,
    )

    now = datetime.now()
    if not start_date:
        dt_start = datetime(now.year, now.month, now.day)
        start_date_val = dt_start.strftime("%Y-%m-%d")
    else:
        dt_start = datetime.strptime(start_date, "%Y-%m-%d")
        start_date_val = start_date

    dt_end = None
    if end_date:
        dt_end = datetime.strptime(end_date, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59, microsecond=999999
        )

    repo = pl_repo.PriceLogRepository(db)
    cmd = pl_cmd.PriceLogGetCommand(
        start_utc_date=dt_start,
        end_utc_date=dt_end,
    )
    logs = await repo.get(
        cmd, limit=limit, title=title, condition=condition, url_filter=url
    )

    context = {
        "logs": logs,
        "filters": {
            "limit": limit,
            "title": title or "",
            "condition": condition or "",
            "url": url or "",
            "start_date": start_date_val,
            "end_date": end_date or "",
        },
    }
    return templates.TemplateResponse(
        request=request, name="pricelog_list.html", context=context
    )
