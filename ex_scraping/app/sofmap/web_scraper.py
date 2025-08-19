from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncSession

from domain.models.pricelog import pricelog as m_pricelog
from databases.sql.pricelog import repository as db_repo
from .constants import A_SOFMAP_NETLOC
import db_convert
from app.getdata.models import search as search_model
from app.getdata import get_search


def is_akiba_sofmap(url: str) -> bool:
    parsed_url = urlparse(url)
    return A_SOFMAP_NETLOC == parsed_url.netloc


def is_valid_url_by_parse(url: str) -> bool:
    try:
        result = urlparse(url)
        return result.netloc and result.scheme
    except ValueError:
        return False


async def save_result(pricelog_list: list[m_pricelog.PriceLog], ses: AsyncSession):
    pricelogrepo = db_repo.PriceLogRepository(ses=ses)
    await pricelogrepo.save_all(pricelog_entries=pricelog_list)


async def download_with_api(
    ses: AsyncSession, searchreq: search_model.SearchRequest, save_to_db: bool = True
):
    if not searchreq.search_keyword and not searchreq.url:
        return False, f"Either search_keyword or url is required."
    if searchreq.url and not is_valid_url_by_parse(searchreq.url):
        return False, f"invalid url , url:{searchreq.url}"
    ok, result = await get_search(searchreq=searchreq)
    if not ok:
        return ok, result
    if isinstance(result, search_model.SearchResults):
        pricelog_list = db_convert.DBModelConvert.searchresult_to_db_models(
            results=result
        )
        if save_to_db:
            await save_result(pricelog_list=pricelog_list, ses=ses)
    return ok, pricelog_list
