from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncSession

from domain.models.pricelog import pricelog as m_pricelog
from databases.sql.pricelog import repository as db_repo

from . import db_convert
from app.getdata.models import search as search_model
from app.getdata import get_search


async def save_result(pricelog_list: list[m_pricelog.PriceLog], ses: AsyncSession):
    pricelogrepo = db_repo.PriceLogRepository(ses=ses)
    await pricelogrepo.save_all(pricelog_entries=pricelog_list)


async def download_with_api(
    ses: AsyncSession, searchreq: search_model.SearchRequest, save_to_db: bool = True
):
    if not searchreq.url:
        return False, f"url is required."
    ok, result = await get_search(searchreq=searchreq)
    if not ok:
        return ok, result
    if not isinstance(result, search_model.SearchResults):
        return False, f"type is not SearchResults, type:{type(result)}, value:{result}"
    pricelog_list = db_convert.DBModelConvert.searchresult_to_db_models(results=result)
    if save_to_db:
        await save_result(pricelog_list=pricelog_list, ses=ses)
    return ok, pricelog_list
