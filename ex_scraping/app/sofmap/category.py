import time

import httpx

from sofmap.parser import CategoryParser
from sofmap.repository import (
    FileCategoryRepository,
    FileAkibaCategoryRepository,
    ICategoryRepository,
)

from .constants import SOFMAP_TOP_URL, A_SOFMAP_TOP_URL


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


def create_category_data():
    def dl_and_create_category(url, repository_class: ICategoryRepository):
        try:
            top_text = dl_sofmap_top(url=url)
            cp = CategoryParser(html_str=top_text)
            cp.execute()
            repo: ICategoryRepository = repository_class()
            repo.save(cate=cp.get_results())
        except Exception:
            return

    dl_and_create_category(url=SOFMAP_TOP_URL, repository_class=FileCategoryRepository)
    dl_and_create_category(
        url=A_SOFMAP_TOP_URL, repository_class=FileAkibaCategoryRepository
    )
