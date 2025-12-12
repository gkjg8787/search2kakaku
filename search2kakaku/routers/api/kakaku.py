import uuid
import re

from fastapi import APIRouter, Depends, HTTPException, Request, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from databases.sql.util import get_async_session
from domain.schemas import schemas
from app.notification import create_item, add_urls, get_items


router = APIRouter(prefix="/kakaku", tags=["kakaku"])
CALLER_TYPE = "api"


def _is_valid_url(url: str) -> bool:
    """URLの形式が有効かどうかをチェックします。"""
    url_pattern = re.compile(
        r"^(?:http|ftp)s?://"  # http:// or https:// or ftp:// or ftps://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # domain...
        r"localhost|"  # localhost...
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # ...or ip
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )
    return re.match(url_pattern, url) is not None


def _validate_urls(urls: list[str]):
    """URLリストのバリデーションを行います。無効なURLがあればHTTPExceptionを送出します。"""
    for url in urls:
        if not _is_valid_url(url):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid URL format: {url}",
            )


@router.post(
    "/items/",
    status_code=status.HTTP_201_CREATED,
    response_model=schemas.KakakuItemCreateResponse,
)
async def create_kakaku_item(
    request: Request,
    request_body: schemas.KakakuItemCreateRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """新規にアイテムを作成します。"""
    run_id = str(uuid.uuid4())
    log = structlog.get_logger(__name__).bind(run_id=run_id, process_type=CALLER_TYPE)
    log.info("Received request to create item", request_body=request_body.model_dump())

    _validate_urls(request_body.urls)

    # `create_item_with_api` は内部でAPIを呼び出すため、ここでは直接レスポンスを返します。
    # 実際のレスポンス形式に合わせて調整してください。
    result = await create_item.create_item_with_api(
        ses=db,
        item_name=request_body.name,
        urls=request_body.urls,
        log=log,
        caller_type=CALLER_TYPE,
    )
    return schemas.KakakuItemCreateResponse(**result)


@router.patch(
    "/items/",
    status_code=status.HTTP_200_OK,
    response_model=schemas.KakakuItemAddURLResponse,
)
async def add_url_to_kakaku_item(
    request: Request,
    request_body: schemas.KakakuItemAddURLRequest,
    db: AsyncSession = Depends(get_async_session),
):
    """既存のアイテムにURLを追加します。"""
    run_id = str(uuid.uuid4())
    log = structlog.get_logger(__name__).bind(run_id=run_id, process_type=CALLER_TYPE)
    log.info(
        "Received request to add URL to item", request_body=request_body.model_dump()
    )

    _validate_urls(request_body.urls)

    result = await add_urls.add_urls_to_item_with_api(
        ses=db,
        item_id=request_body.item_id,
        urls=request_body.urls,
        log=log,
        caller_type=CALLER_TYPE,
    )
    return schemas.KakakuItemAddURLResponse(**result)


@router.get("/items/", response_model=schemas.KakakuItemGetResponse)
async def get_kakaku_item(
    request: Request,
    urls: list[str] = Query(..., description="関連アイテムを取得するURLのリスト"),
    db: AsyncSession = Depends(get_async_session),
):
    """指定したURLから関連のアイテム一覧を取得します。"""
    run_id = str(uuid.uuid4())
    log = structlog.get_logger(__name__).bind(run_id=run_id, process_type=CALLER_TYPE)
    log.info("Received request to get items by URL", urls=urls)

    _validate_urls(urls)

    results, err_msgs = await get_items.get_items_by_url_with_api(
        ses=db, urls=urls, log=log, caller_type=CALLER_TYPE
    )
    return schemas.KakakuItemGetResponse(results=results, err_msg=",".join(err_msgs))
