import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from databases.sql.util import get_async_session
from app.update import update_urls, view_urls
from domain.schemas import schemas
from app.update.update_urls import RegisterURLByURL, RegisterURLByID


router = APIRouter(prefix="/urls", tags=["urls"])


@router.get("/", response_model=schemas.ViewURLResponse)
async def get_update_urls(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    id: int | None = Query(default=None),
    url: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    view_option: bool = Query(default=True),
):
    run_id = str(uuid.uuid4())
    log = structlog.get_logger(__name__).bind(run_id=run_id, process_type="api_request")
    log.info(
        "Received request to get update URLs",
        is_active=is_active,
        view_option=view_option,
    )

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
    log.info("Successfully retrieved update URLs", count=len(results))
    return response


@router.post(
    "/",
    response_model=schemas.UpdateNotificationResultResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_urls_api(
    request: Request,
    request_body: schemas.URLRegisterRequest,
    db: AsyncSession = Depends(get_async_session),
):
    run_id = str(uuid.uuid4())
    log = structlog.get_logger(__name__).bind(run_id=run_id, process_type="api_request")
    log.info(
        "Received request to register URLs by URL string",
        urls=request_body.urls,
        sitename=request_body.sitename,
        options=request_body.options,
    )
    if not request_body.urls:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="No URLs provided"
        )

    target_urls = [
        RegisterURLByURL(
            url=url,
            sitename=request_body.sitename or "",
            options=request_body.options or {},
        )
        for url in request_body.urls
    ]
    result = await update_urls.register_urls(ses=db, target_urls=target_urls)
    log.info("Finished registering URLs by URL string", result=result.model_dump())
    return result


@router.post(
    "/actions/register-all",
    response_model=schemas.UpdateNotificationResultResponse,
    status_code=status.HTTP_200_OK,
)
async def register_all_urls_action(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    run_id = str(uuid.uuid4())
    log = structlog.get_logger(__name__).bind(run_id=run_id, process_type="api_request")
    log.info("Received request to register all URLs")

    target_db_urls = await update_urls.get_target_db_urls(ses=db)
    if not target_db_urls:
        log.warning("No URLs found in database to register all")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No URLs found in database"
        )
    result = await update_urls.register_all_urls(ses=db, target_urls=target_db_urls)
    log.info("Finished registering all URLs", result=result.model_dump())
    return result


@router.post(
    "/actions/register-new",
    response_model=schemas.UpdateNotificationResultResponse,
    status_code=status.HTTP_200_OK,
)
async def register_new_urls_action(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    run_id = str(uuid.uuid4())
    log = structlog.get_logger(__name__).bind(run_id=run_id, process_type="api_request")
    log.info("Received request to register new URLs")

    target_db_urls = await update_urls.get_target_db_urls(ses=db)
    if not target_db_urls:
        log.warning("No URLs found in database to register new")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No URLs found in database"
        )
    result = await update_urls.register_new_urls(ses=db, target_urls=target_db_urls)
    log.info("Finished registering new URLs", result=result.model_dump())
    return result


@router.patch(
    "/",
    response_model=schemas.UpdateNotificationResultResponse,
    status_code=status.HTTP_200_OK,
)
async def update_urls_api(
    request: Request,
    request_body: schemas.URLRegisterRequest,
    db: AsyncSession = Depends(get_async_session),
):
    run_id = str(uuid.uuid4())
    log = structlog.get_logger(__name__).bind(run_id=run_id, process_type="api_request")
    log.info(
        "Received request to update/re-enable URLs",
        url_ids=request_body.url_ids,
        urls=request_body.urls,
        sitename=request_body.sitename,
        options=request_body.options,
    )
    if request_body.url_ids:
        target_urls = [
            RegisterURLByID(
                url_id=url_id,
                sitename=request_body.sitename or "",
                options=request_body.options or {},
            )
            for url_id in request_body.url_ids
        ]
    else:
        target_urls = [
            RegisterURLByURL(
                url=url,
                sitename=request_body.sitename or "",
                options=request_body.options or {},
            )
            for url in request_body.urls
        ]

    result = await update_urls.update_registered_urls(ses=db, targets=target_urls)
    log.info("Finished updating/re-enabling URLs", result=result.model_dump())
    return result


@router.patch(
    "/inactive",
    response_model=schemas.UpdateNotificationResultResponse,
    status_code=status.HTTP_200_OK,
)
async def inactive_urls_api(
    request: Request,
    request_body: schemas.URLRemoveRequest,
    db: AsyncSession = Depends(get_async_session),
):
    run_id = str(uuid.uuid4())
    log = structlog.get_logger(__name__).bind(run_id=run_id, process_type="api_request")
    log.info(
        "Received request to inactive URLs by ID",
        url_ids=request_body.url_ids,
        urls=request_body.urls,
    )
    if request_body.url_ids:
        target_urls = request_body.url_ids
    else:
        target_urls = request_body.urls
    result = await update_urls.inactive_urls(ses=db, target_urls=target_urls)
    log.info("Finished inactivating URLs by ID", result=result.model_dump())
    return result


@router.patch(
    "/actions/inactive-all",
    response_model=schemas.UpdateNotificationResultResponse,
    status_code=status.HTTP_200_OK,
)
async def inactive_all_urls_action(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    run_id = str(uuid.uuid4())
    log = structlog.get_logger(__name__).bind(run_id=run_id, process_type="api_request")
    log.info("Received request to inactive all URLs")

    target_db_urls = await update_urls.get_target_db_urls(ses=db)
    if not target_db_urls:
        log.warning("No URLs found in database to inactive all")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No URLs found in database"
        )
    result = await update_urls.inactive_all_urls(ses=db, target_urls=target_db_urls)
    log.info("Finished inactivating all URLs", result=result.model_dump())
    return result
