import sys
import argparse
from app.sofmap import urlgenerate

SHIFT_JIS = "shift_jis"
UTF8 = "utf-8"


def set_argparse(argv):
    parser = argparse.ArgumentParser(
        description="ウェブサイトから情報を検索するスクリプト。",
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
        "-c",
        "--category",
        type=str,
        help="検索対象のカテゴリ文字列（例: 'テクノロジー'、'ニュース'）",
    )
    parser.add_argument(
        "-pd",
        "--product_type",
        type=str,
        help="検索対象の商品状態の文字列（例: 'NEW'、'USED'）",
    )

    return parser.parse_args(argv[1:])


def main(argv):
    argp = set_argparse(argv)
    print(argp.search_query)
    print(argp.akiba)
    print(argp.category)
    if argp.akiba:
        base_url = urlgenerate.A_BASE_URL
    else:
        base_url = urlgenerate.BASE_SEARCH_URL
    result = urlgenerate.build_search_url(
        base_url=base_url,
        search_keyword=argp.search_query,
        query_encode_type=SHIFT_JIS,
    )
    print(result)


if __name__ == "__main__":
    main(sys.argv)
