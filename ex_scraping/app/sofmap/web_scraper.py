from urllib.parse import urlparse
from typing import Any
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from domain.models.pricelog import pricelog as m_pricelog
from databases.sqldb import util as db_util
from databases.sqldb.pricelog import repository as db_repo
from sofmap.parser import SofmapParser
from . import cookie_util, download, db_convert
from .constants import A_SOFMAP_NETLOC


class ScrapeCommand(BaseModel):
    url: str
    is_ucaa: bool = Field(default=False)
    async_session: Any


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


async def scrape_and_save(command: ScrapeCommand):
    if not is_valid_url_by_parse(command.url):
        return False, f"invalid url ,{command.url}"
    is_a_sofmap = is_akiba_sofmap(command.url)
    cookie_dict_list = cookie_util.create_cookies(
        is_akiba=is_a_sofmap, is_ucaa=command.is_ucaa
    )
    try:
        html = download.download_remotely(
            url=command.url, cookie_dict_list=cookie_dict_list
        )
    except Exception as e:
        return False, f"download error, {e}"
    db_util.create_db_and_tables()
    sparser = SofmapParser(html_str=html)
    sparser.execute(url=command.url)
    results = sparser.get_results()
    pricelog_list = db_convert.DBModelConvert.parseresults_to_db_model(results=results)
    await save_result(pricelog_list=pricelog_list, ses=command.async_session)
    return True, ""
