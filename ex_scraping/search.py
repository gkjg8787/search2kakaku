import argparse
import asyncio
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from sofmap import parser
from domain.models.pricelog import repository as m_repo, command as p_cmd
from app.sofmap import (
    category as app_cate,
    urlgenerate,
    download,
    db_convert,
    cookie_util,
    constants as sofmap_const,
)
from domain.models.pricelog import pricelog as m_pricelog
from databases.sqldb.pricelog import repository as db_repo
from databases.sqldb import util as db_util
from common import read_config, logger_config


class SiteName:
    sofmap = "sofmap"


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
    CONDITIONS = [pt.name for pt in urlgenerate.ProductTypeOptions]
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
    orderbys = [member.name for member in urlgenerate.OrderByOptions]
    sofmap_parser.add_argument(
        "-o",
        "--orderby",
        type=lambda s: str(s).upper(),
        choices=orderbys,
        default=urlgenerate.OrderByOptions.DEFAULT.name,
        help=f'検索の並び順: {", ".join(orderbys)}',
    )
    sofmap_parser.add_argument(
        "--ucaa",
        action="store_true",
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
    ses: AsyncSession,
    repository: m_repo.ICategoryRepository,
    is_akiba: bool,
) -> list[str]:
    if is_akiba:
        entity_type = sofmap_const.A_SOFMAP_DB_ENTITY_TYPE
    else:
        entity_type = sofmap_const.SOFMAP_DB_ENTITY_TYPE
    getcmd = p_cmd.CategoryGetCommand(entity_type=entity_type)
    results = await repository.get(command=getcmd)
    if not results:
        await app_cate.create_category_data(ses=ses)

    results = await repository.get(command=getcmd)
    if not results:
        return []
    return [r.name for r in results]


async def get_category_id(
    ses: AsyncSession,
    repository: m_repo.ICategoryRepository,
    is_akiba: bool,
    category_name: str,
) -> str:
    if not category_name:
        return ""
    if is_akiba:
        entity_type = sofmap_const.A_SOFMAP_DB_ENTITY_TYPE
    else:
        entity_type = sofmap_const.SOFMAP_DB_ENTITY_TYPE
    getcmd = p_cmd.CategoryGetCommand(name=category_name, entity_type=entity_type)
    results = await repository.get(command=getcmd)
    if not results:
        await app_cate.create_category_data(ses=ses)

    results = await repository.get(command=getcmd)
    if not results:
        return ""
    return results[0].category_id


async def save_result(ses: AsyncSession, pricelog_list: list[m_pricelog.PriceLog]):
    pricelogrepo = db_repo.PriceLogRepository(ses=ses)
    await pricelogrepo.save_all(pricelog_entries=pricelog_list)


async def sofmap_command(argp, log):
    db_util.create_db_and_tables()
    async for ses in db_util.get_async_session():
        if argp.categorylist:
            category_list = await get_category_list(
                ses=ses,
                repository=db_repo.CategoryRepository(ses=ses),
                is_akiba=argp.akiba,
            )
            log.info(category_list)
            return
        if not argp.search_query:
            log.info("paramter error. search_query is None")
            return
        gid = await get_category_id(
            ses=ses,
            repository=db_repo.CategoryRepository(ses=ses),
            is_akiba=argp.akiba,
            category_name=argp.category,
        )
        log.info("get parameter", gid=gid, **vars(argp))
        search_url = urlgenerate.build_search_url(
            search_keyword=argp.search_query,
            is_akiba=argp.akiba,
            direct_search=argp.direct_search,
            gid=gid,
            product_type=argp.condition,
            display_count=argp.displaycount,
            order_by=argp.orderby,
        )
        log.info("generate url", search_url=search_url)
        cookie_dict_list = cookie_util.create_cookies(
            is_akiba=argp.akiba, is_ucaa=argp.ucaa
        )
        sofmapopt = read_config.get_sofmap_options()
        seleniumopt = read_config.get_selenium_options()
        try:
            html = download.download_remotely(
                url=search_url,
                cookie_dict_list=cookie_dict_list,
                page_load_timeout=sofmapopt.selenium.page_load_timeout,
                tag_wait_timeout=sofmapopt.selenium.tag_wait_timeout,
                selenium_url=seleniumopt.remote_url,
            )
        except Exception as e:
            log.error(f"download error {e}", url=search_url)
            return
        log.info("download end")
        sparser = parser.SearchResultParser(html_str=html, url=search_url)
        sparser.execute()
        results = sparser.get_results()
        pricelog_list = db_convert.DBModelConvert.parseresults_to_db_model(
            results=results, remove_duplicate=True
        )
        if not pricelog_list:
            log.info("data is None")
            return
        if not argp.without_registration:
            await save_result(ses=ses, pricelog_list=pricelog_list)
            log.info("save to database")
        if argp.verbose:
            log.info(pricelog_list, verbose=True)
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
