import time

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from sofmap.parser import CategoryParser
from sofmap.model import CategoryResult
from domain.models.pricelog import repository as p_repo, pricelog as m_pricelog
from databases.sql.pricelog.repository import CategoryRepository

from .constants import (
    SOFMAP_TOP_URL,
    A_SOFMAP_TOP_URL,
    SOFMAP_DB_ENTITY_TYPE,
    A_SOFMAP_DB_ENTITY_TYPE,
)


def dl_sofmap_top(
    url: str, max_retries: int = 2, delay_seconds: int = 1, timeout: int = 4
):
    for attempt in range(max_retries + 1):
        try:
            res = httpx.get(url, timeout=timeout)
            res.raise_for_status()
            return res.text
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            if attempt < max_retries:
                time.sleep(delay_seconds)
            else:
                raise e
        except Exception as e:
            raise e


def convert_categoryresult_to_categorydomain(
    result: CategoryResult, entity_type: str
) -> list[m_pricelog.Category]:
    domain_list: list[m_pricelog.Category] = []
    for gid, name in result.gid_to_name.items():
        domain_list.append(
            m_pricelog.Category(category_id=gid, name=name, entity_type=entity_type)
        )
    return domain_list


async def create_category_data(ses: AsyncSession):
    async def dl_and_create_category(
        url, repository: p_repo.ICategoryRepository, entity_type: str
    ):
        try:
            top_text = dl_sofmap_top(url=url)
            cp = CategoryParser(html_str=top_text)
            cp.execute()
            category_list = convert_categoryresult_to_categorydomain(
                result=cp.get_results(), entity_type=entity_type
            )
            await repository.save_all(cate_entries=category_list)
        except Exception:
            return

    repository = CategoryRepository(ses=ses)
    await dl_and_create_category(
        url=SOFMAP_TOP_URL, repository=repository, entity_type=SOFMAP_DB_ENTITY_TYPE
    )
    await dl_and_create_category(
        url=A_SOFMAP_TOP_URL, repository=repository, entity_type=A_SOFMAP_DB_ENTITY_TYPE
    )
