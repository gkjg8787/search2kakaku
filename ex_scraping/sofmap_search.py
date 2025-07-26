import sys
import argparse
import asyncio

from sofmap import repository, parser
from app.sofmap import (
    category as app_cate,
    urlgenerate,
    download,
    db_convert,
    cookie_util,
)
from domain.models.pricelog import pricelog as m_pricelog
from databases.sqldb.pricelog import repository as db_repo
from databases.sqldb import util as db_util
from common import read_config


def set_argparse(argv):
    parser = argparse.ArgumentParser(
        description="sofmapを検索し結果をデータベースに保存するスクリプト。",
        formatter_class=argparse.RawTextHelpFormatter,  # ヘルプメッセージの整形を保持
    )

    # 1つ目の引数: 検索ワード (必須の位置引数)
    parser.add_argument(
        "search_query",
        type=str,
        help="検索したいキーワード（例: 'マリオカートワールド'）",
    )
    parser.add_argument(
        "-a",
        "--akiba",
        action="store_true",
        help="検索対象サイトをwww.sofmap.comからa.sofmap.comに変更します。",
    )
    parser.add_argument(
        "-ca",
        "--category",
        type=str,
        help="検索対象のカテゴリ文字列（例: 'PCパーツ'、'スマートフォン'）。完全一致のみ有効",
    )
    CONDITIONS = [pt.name for pt in urlgenerate.ProductTypeOptions]
    parser.add_argument(
        "-co",
        "--condition",
        type=lambda s: str(s).upper(),
        choices=CONDITIONS,
        help=f'検索対象の商品状態: {", ".join(CONDITIONS)}',
    )
    parser.add_argument(
        "-ds",
        "--direct_search",
        action="store_true",
        help="検索対象のサイトをショートカットします。",
    )
    parser.add_argument(
        "-dc",
        "--displaycount",
        type=int,
        default=50,
        help=f"検索対象の表示件数。初期値50",
    )
    orderbys = [member.name for member in urlgenerate.OrderByOptions]
    parser.add_argument(
        "-o",
        "--orderby",
        type=lambda s: str(s).upper(),
        choices=orderbys,
        default=urlgenerate.OrderByOptions.DEFAULT.name,
        help=f'検索の並び順: {", ".join(orderbys)}',
    )
    parser.add_argument(
        "--ucaa",
        action="store_true",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="結果を標準出力",
    )

    return parser.parse_args(argv[1:])


def get_category_id(
    repository: repository.ICategoryRepository, category_name: str
) -> str:
    if not category_name:
        return ""
    if not repository.has_data():
        app_cate.create_category_data()
        if not repository.has_data():
            return ""
    return repository.get_gid(name=category_name)


async def save_result(pricelog_list: list[m_pricelog.PriceLog]):
    async for ses in db_util.get_async_session():
        pricelogrepo = db_repo.PriceLogRepository(ses=ses)
        await pricelogrepo.save_all(pricelog_entries=pricelog_list)


def main(argv):
    if len(argv) == 1:
        print("parameter error. param length zero")
        return
    argp = set_argparse(argv)
    if not argp.search_query:
        print("paramter error. search_query is None")
        return
    if argp.akiba:
        cate_repo = repository.FileAkibaCategoryRepository()
    else:
        cate_repo = repository.FileCategoryRepository()
    gid = get_category_id(repository=cate_repo, category_name=argp.category)
    print(f"keyword : {argp.search_query}, gid : {gid}, is_akiba : {argp.akiba}")
    search_url = urlgenerate.build_search_url(
        search_keyword=argp.search_query,
        is_akiba=argp.akiba,
        direct_search=argp.direct_search,
        gid=gid,
        product_type=argp.condition,
        display_count=argp.displaycount,
        order_by=argp.orderby,
    )
    print(f"generate url : {search_url}")
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
        print(f"download error {e}")
        return
    print(f"download end")
    db_util.create_db_and_tables()
    sparser = parser.SofmapParser(html_str=html)
    sparser.execute(url=search_url)
    results = sparser.get_results()
    pricelog_list = db_convert.DBModelConvert.parseresults_to_db_model(
        results=results, remove_duplicate=True
    )
    asyncio.run(save_result(pricelog_list=pricelog_list))
    print(f"save to database")
    if argp.verbose:
        print(pricelog_list)


if __name__ == "__main__":
    main(sys.argv)
