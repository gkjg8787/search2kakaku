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
from app.sofmap.constants import A_BASE_SEARCH_URL, BASE_SEARCH_URL
from domain.models.pricelog import pricelog as m_pricelog
from databases.sqldb.pricelog import repository as db_repo
from databases.sqldb import util as db_util


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

    # 2つ目の引数: 対象サイト変更オプション (-a)
    # action='store_true' は、引数が指定された場合にTrue、指定されない場合にFalseを格納する
    parser.add_argument(
        "-a",
        "--akiba",
        action="store_true",
        help="検索対象サイトをwww.sofmap.comからa.sofmap.comに変更します。",
    )

    # 3つ目の引数: カテゴリ文字列 (オプション)
    parser.add_argument(
        "-c",
        "--category",
        type=str,
        help="検索対象のカテゴリ文字列（例: 'PCパーツ'、'スマートフォン'）。完全一致のみ有効",
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
        base_url = A_BASE_SEARCH_URL
    else:
        cate_repo = repository.FileCategoryRepository()
        base_url = BASE_SEARCH_URL
    gid = get_category_id(repository=cate_repo, category_name=argp.category)
    print(f"keyword : {argp.search_query}, gid : {gid}, base_url : {base_url}")
    search_url = urlgenerate.build_search_url(
        search_keyword=argp.search_query, base_url=base_url, gid=gid
    )
    print(f"generate url : {search_url}")
    cookie_dict_list = cookie_util.create_cookies(
        is_akiba=argp.akiba, is_ucaa=argp.ucaa
    )
    try:
        html = download.download_remotely(
            url=search_url, cookie_dict_list=cookie_dict_list
        )
    except Exception as e:
        print(f"download error {e}")
        return
    print(f"download end")
    db_util.create_db_and_tables()
    sparser = parser.SofmapParser(html_str=html)
    sparser.execute(url=search_url)
    results = sparser.get_results()
    pricelog_list = db_convert.DBModelConvert.parseresults_to_db_model(results=results)
    asyncio.run(save_result(pricelog_list=pricelog_list))
    print(f"save to database")
    if argp.verbose:
        print(pricelog_list)


if __name__ == "__main__":
    main(sys.argv)
