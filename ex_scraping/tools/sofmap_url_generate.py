import sys
import argparse
from app.sofmap import urlgenerate

SHIFT_JIS = "shift_jis"
UTF8 = "utf-8"


def set_argparse(argv):
    parser = argparse.ArgumentParser(
        description="sofmapの検索用URL作成スクリプト。",
        formatter_class=argparse.RawTextHelpFormatter,  # ヘルプメッセージの整形を保持
    )

    # 1つ目の引数: 検索ワード (必須の位置引数)
    parser.add_argument(
        "search_query",
        type=str,
        help="検索したいキーワード（例: 'Pythonプログラミング'）",
    )

    # 2つ目の引数: 対象サイト変更オプション (-a)
    # action='store_true' は、引数が指定された場合にTrue、指定されない場合にFalseを格納する
    parser.add_argument(
        "-a",
        "--akiba",
        action="store_true",
        help="対象サイトをwww.sofmap.comからa.sofmap.comに変更します。",
    )

    # 3つ目の引数: カテゴリ文字列 (オプション)
    parser.add_argument(
        "-g",
        "--gid",
        type=str,
        default="",
        help="検索対象のカテゴリのID（例: '002110020010')",
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

    return parser.parse_args(argv[1:])


def main(argv):
    argp = set_argparse(argv)
    print(argp)
    result = urlgenerate.build_search_url(
        is_akiba=argp.akiba,
        search_keyword=argp.search_query,
        query_encode_type=SHIFT_JIS,
        product_type=argp.condition,
        direct_search=argp.direct_search,
        gid=argp.gid,
        display_count=argp.displaycount,
        order_by=argp.orderby,
    )
    print(result)


if __name__ == "__main__":
    main(sys.argv)
