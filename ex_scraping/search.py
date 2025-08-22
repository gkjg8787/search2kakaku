import argparse
import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
import structlog


from app.sofmap import (
    web_scraper as sofmap_scraper,
    enums as sofmap_enums,
    models as sofmap_models,
)
from domain.models.pricelog import pricelog as m_pricelog
from databases.sql.pricelog import repository as db_repo
from databases.sql import util as db_util
from common import logger_config
from app.getdata import get_search_info
from app.getdata.models import info as info_model, search as search_model
from app.sofmap.constants import SiteName


def set_argparse():
    parser = argparse.ArgumentParser(
        description="サイトを検索し結果をデータベースに保存するスクリプト。",
        formatter_class=argparse.RawTextHelpFormatter,  # ヘルプメッセージの整形を保持
    )
    subparsers = parser.add_subparsers(
        dest="sitename", help="検索対象サイト", required=True
    )

    sofmap_parser = subparsers.add_parser(
        SiteName.sofmap,
        help="sofmapを検索",
    )
    sofmap_parser.add_argument(
        "search_query",
        nargs="?",
        help="検索したいキーワード（例: 'マリオカートワールド'）",
    )
    sofmap_parser.add_argument(
        "-a",
        "--akiba",
        action="store_true",
        help="検索対象サイトをwww.sofmap.comからa.sofmap.comに変更します。",
    )
    sofmap_parser.add_argument(
        "-ca",
        "--category",
        type=str,
        help="検索対象のカテゴリ文字列（例: 'PCパーツ'、'スマートフォン'）。完全一致のみ有効",
    )
    sofmap_parser.add_argument(
        "--categorylist",
        action="store_true",
        help="検索対象のカテゴリ一覧を表示します。このオプションを指定した場合、検索はされません。",
    )
    CONDITIONS = [pt.name for pt in sofmap_enums.ProductTypeOptions]
    sofmap_parser.add_argument(
        "-co",
        "--condition",
        type=lambda s: str(s).upper(),
        choices=CONDITIONS,
        help=f'検索対象の商品状態: {", ".join(CONDITIONS)}',
    )
    sofmap_parser.add_argument(
        "-ds",
        "--direct_search",
        action="store_true",
        help="検索をメインサイトではなくメインサイトから呼び出しているデータ取得URLへ変更します。価格情報の取得が正常に動作しないかもしれません。",
    )
    sofmap_parser.add_argument(
        "-dc",
        "--displaycount",
        type=int,
        default=50,
        help=f"検索対象の表示件数。初期値50",
    )
    orderbys = [member.name for member in sofmap_enums.OrderByOptions]
    sofmap_parser.add_argument(
        "-o",
        "--orderby",
        type=lambda s: str(s).upper(),
        choices=orderbys,
        default=sofmap_enums.OrderByOptions.DEFAULT.name,
        help=f'検索の並び順: {", ".join(orderbys)}',
    )
    sofmap_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="結果を標準出力",
    )
    sofmap_parser.add_argument(
        "--without_registration",
        action="store_true",
        help="作成したURL含む、結果をデータベースに登録しない",
    )

    return parser.parse_args()


async def get_category_list(
    sitename: str,
    is_akiba: bool,
) -> list[dict]:
    inforeq = info_model.InfoRequest(
        sitename=sitename, infoname="category", options={"is_akiba": is_akiba}
    )
    ok, result = await get_search_info(inforeq=inforeq)
    if ok and isinstance(result, info_model.InfoResponse):
        return [r.model_dump() for r in result.results]
    return []


async def get_category_id(
    sitename: str,
    is_akiba: bool,
    category_name: str,
) -> str:
    if not category_name:
        return ""
    result = await get_category_list(sitename=sitename, is_akiba=is_akiba)
    if not result:
        return ""
    for r in result:
        if r["name"] == category_name:
            return r["gid"]
    return ""


async def save_result(ses: AsyncSession, pricelog_list: list[m_pricelog.PriceLog]):
    pricelogrepo = db_repo.PriceLogRepository(ses=ses)
    await pricelogrepo.save_all(pricelog_entries=pricelog_list)


async def sofmap_command(argp, log):
    db_util.create_db_and_tables()
    async for ses in db_util.get_async_session():
        if argp.categorylist:
            category_list = await get_category_list(
                sitename=SiteName.sofmap,
                is_akiba=argp.akiba,
            )
            log.info(category_list)
            return
        if not argp.search_query:
            log.info("paramter error. search_query is None")
            return
        gid = await get_category_id(
            sitename=SiteName.sofmap,
            is_akiba=argp.akiba,
            category_name=argp.category,
        )
        log.info("get parameter", gid=gid, **vars(argp))
        searchoptions = sofmap_models.SofmapSearchDataOptions(
            is_akiba=argp.akiba,
            direct_search=argp.direct_search,
            gid=gid,
            product_type=argp.condition,
            display_count=argp.displaycount,
            order_by=argp.orderby,
        )
        searchreq = search_model.SearchRequest(
            url="",
            search_keyword=argp.search_query,
            sitename=SiteName.sofmap,
            options=searchoptions.model_dump(exclude_none=True),
        )

        log.info("setting params", searchreq=searchreq.model_dump())
        try:
            ok, result = await sofmap_scraper.download_with_api(
                ses=ses, searchreq=searchreq, save_to_db=not argp.without_registration
            )
            if not ok:
                log.error("download failed", error_msg=result)
                return
        except Exception as e:
            log.error(f"download error type:{type(e).__name__}, {e}")
            return
        log.info("download end")
        if not isinstance(result, list):
            log.error(f"result is not list. type :{type(result)}", result=result)
            return
        if not result:
            log.info("data is None")
            return
        if argp.without_registration:
            log.info("data is save")
        if argp.verbose:
            log.info(result, verbose=True)
    return


async def main():
    logger_config.configure_logger()
    run_id = str(uuid.uuid4())
    log = structlog.get_logger(__name__).bind(
        run_id=run_id, process_type="sofmap_search"
    )

    argp = set_argparse()
    if argp.sitename == SiteName.sofmap:
        await sofmap_command(argp=argp, log=log)


if __name__ == "__main__":
    asyncio.run(main())
