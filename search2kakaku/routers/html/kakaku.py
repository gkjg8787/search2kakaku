import uuid

from fastapi import APIRouter, Request, Depends, Form, status, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from databases.sql.util import get_async_session
from common import read_template, read_config
from app.update import view_urls
from domain.schemas import schemas
from app.notification import get_items

router = APIRouter(prefix="/kakaku", tags=["view_kakaku"])
templates = read_template.templates
CALLER_TYPE = "html.kakaku"


@router.get("/", response_class=HTMLResponse, name="kakaku_list")
async def read_kakaku_list(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    view_option: bool = Query(default=False),
    active_filter: str | None = Query(default=None),
):
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        router_path=request.url.path,
        request_id=str(uuid.uuid4()),
        caller=CALLER_TYPE,
    )
    log = structlog.get_logger()
    log.info("Reading all url to kakaku")
    # Map active_filter (if provided) to is_active for repository query
    if active_filter is not None:
        af = active_filter.lower()
        if af == "active":
            query_is_active = True
        elif af == "inactive":
            query_is_active = False
        else:
            # 'all' or any other value -> no filtering on is_active
            query_is_active = None
    else:
        query_is_active = None

    viewrepo = view_urls.ViewURLActiveRepository(ses=db)
    db_urls = await viewrepo.get(
        command=view_urls.ViewURLActiveGetCommand(
            view_option=view_option, is_active=query_is_active
        )
    )
    urls = [db_url.url for db_url in db_urls]
    results, err_msgs = await get_items.get_items_by_url_with_api(
        ses=db, urls=urls, log=log, caller_type=CALLER_TYPE
    )

    context = schemas.KakakuListContext(
        results=results, error_msgs=err_msgs, active_filter=active_filter
    )
    htmlopts = read_config.get_html_options()
    if htmlopts.kakaku and htmlopts.kakaku.to_link:
        context.to_link = htmlopts.kakaku.to_link

    return templates.TemplateResponse(
        request=request, name="kakaku_list.html", context=context.model_dump()
    )


@router.get("/add/", response_class=HTMLResponse, name="add_url_to_kakaku_form")
async def add_url_to_kakaku_form(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    url_id: int | None = Query(default=None),
    url: str | None = Query(default=None),
):
    if url_id is None and not url:
        raise HTTPException(status_code=400, detail="Invalid request")
    if url_id:
        viewrepo = view_urls.ViewURLActiveRepository(ses=db)
        db_urls = await viewrepo.get(
            command=view_urls.ViewURLActiveGetCommand(id=url_id, view_option=True)
        )
        if not db_urls:
            raise HTTPException(status_code=404, detail="URL not found")
        url = db_urls[0].url
    elif url:
        viewrepo = view_urls.ViewURLActiveRepository(ses=db)
        db_urls = await viewrepo.get(
            command=view_urls.ViewURLActiveGetCommand(url=url, view_option=True)
        )
        if not db_urls:
            raise HTTPException(status_code=404, detail="URL not found")
        url_id = db_urls[0].id

    context = {"url_id": url_id, "url": url}
    return templates.TemplateResponse(
        request=request, name="kakaku_add.html", context=context
    )
