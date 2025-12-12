import uuid
import json

from fastapi import APIRouter, Request, Depends, Form, status, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from databases.sql.util import get_async_session
from common import read_template, read_config
from app.update import view_urls
from domain.schemas import schemas

router = APIRouter(prefix="/url", tags=["url"])
templates = read_template.templates
CALLER_TYPE = "html.url"


@router.get("/", response_class=HTMLResponse, name="url_list")
async def read_urls(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    id: int | None = Query(default=None),
    url: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    view_option: bool = Query(default=True),
):
    """登録URL一覧ページ"""
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        router_path=request.url.path,
        request_id=str(uuid.uuid4()),
        caller=CALLER_TYPE,
    )
    log = structlog.get_logger()
    log.info("Reading all urls")
    viewrepo = view_urls.ViewURLActiveRepository(ses=db)
    results = await viewrepo.get(
        command=view_urls.ViewURLActiveGetCommand(
            id=id, url=url, is_active=is_active, view_option=view_option
        )
    )
    response = schemas.ViewURLResponse(
        view_urls=[
            schemas.ViewURLActive(
                id=r.id,
                url=r.url,
                sitename=r.sitename,
                is_active=r.is_active,
                options=r.meta,
            )
            for r in results
        ]
    )
    context = response.model_dump()
    config = read_config.get_html_options()
    if config.kakaku and config.kakaku.to_link:
        context["to_link"] = config.kakaku.to_link
    return templates.TemplateResponse(
        request=request, name="url_list.html", context=context
    )


@router.get("/add/", response_class=HTMLResponse, name="add_url_form")
async def add_url_form(
    request: Request,
    url: str | None = Query(default=None),
    sitename: str | None = Query(default=None),
    options: str | None = Query(default=None),
):
    """URL追加ページ"""
    try:
        options_json = json.loads(options) if options else None
    except json.JSONDecodeError:
        options_json = None
    context = {"url": url, "sitename": sitename, "options": options_json or {}}
    config = read_config.get_html_options()
    if config.kakaku and config.kakaku.to_link:
        context["to_link"] = config.kakaku.to_link
    return templates.TemplateResponse(
        request=request, name="url_add.html", context=context
    )


@router.get("/update/{url_id}", response_class=HTMLResponse, name="update_url_form")
async def update_url_form(
    request: Request,
    url_id: int,
    db: AsyncSession = Depends(get_async_session),
):
    """URL更新ページ"""
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        router_path=request.url.path,
        request_id=str(uuid.uuid4()),
        caller=CALLER_TYPE,
        url_id=url_id,
    )
    log = structlog.get_logger()
    log.info("Getting url for update form")
    viewrepo = view_urls.ViewURLActiveRepository(ses=db)
    db_urls = await viewrepo.get(
        command=view_urls.ViewURLActiveGetCommand(id=url_id, view_option=True)
    )
    if not db_urls:
        raise HTTPException(status_code=404, detail="URL not found")
    if len(db_urls) > 1:
        raise HTTPException(status_code=400, detail="Multiple URLs found")
    db_url = schemas.ViewURLActive(
        id=db_urls[0].id,
        url=db_urls[0].url,
        sitename=db_urls[0].sitename,
        is_active=db_urls[0].is_active,
        options=db_urls[0].meta,
    )
    context = {"url": db_url}
    config = read_config.get_html_options()
    if config.kakaku and config.kakaku.to_link:
        context["to_link"] = config.kakaku.to_link
    return templates.TemplateResponse(
        request=request, name="url_update.html", context=context
    )
