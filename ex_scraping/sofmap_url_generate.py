import sys
import argparse
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode, quote_plus

SHIFT_JIS = "shift_jis"
UTF8 = "utf-8"


def build_search_url(
    base_url, search_query, query_param_name="q", query_encode_type=UTF8, gid=""
):
    """
    検索ワードをURLエンコードし、ベースURLのクエリパラメータとして追加する。

    Args:
        base_url (str): 検索サイトのベースURL（例: "https://www.google.com/search"）。
        search_query (str): URLエンコードしたい検索ワード。
        query_param_name (str): 検索ワードを渡すクエリパラメータの名前（デフォルトは'q'）。

    Returns:
        str: 検索ワードが追加された完成したURL。
    """
    # 検索ワードをURLエンコード
    encoded_query = quote_plus(search_query, encoding=query_encode_type)

    # ベースURLを解析
    parsed_base_url = urlparse(base_url)

    # 既存のクエリパラメータを辞書に変換
    # parse_qs はクエリ文字列を辞書にパースする
    query_params = parse_qs(parsed_base_url.query)

    # 新しい検索ワードをクエリパラメータに追加/更新
    query_params[query_param_name] = [encoded_query]  # quote_plusでエンコード済み
    if gid:
        query_params["gid"] = gid

    # 辞書をURLエンコードされたクエリ文字列に変換
    # doseq=True は値がリストの場合に 'key=val1&key=val2' のように展開する
    # safe='' はデフォルトで '/' もエンコードしないが、quote_plusで処理済みなので特に指定不要
    new_query_string = urlencode(query_params, doseq=True)

    # 解析したURLコンポーネメントを再構築して、新しいクエリ文字列を組み込む
    # urlunparse((scheme, netloc, path, params, query, fragment))
    # query_string は既にエンコードされているため、quote_plusは不要
    final_url = urlunparse(
        (
            parsed_base_url.scheme,
            parsed_base_url.netloc,
            parsed_base_url.path,
            parsed_base_url.params,
            new_query_string,  # ここにエンコードされたクエリ文字列を渡す
            parsed_base_url.fragment,
        )
    )

    return final_url


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

    return parser.parse_args(argv[1:])


def main(argv):
    argp = set_argparse(argv)
    print(argp.search_query)
    print(argp.akiba)
    print(argp.category)
    if argp.akiba:
        base_url = "https://a.sofmap.com/search_result.aspx"
    else:
        base_url = "https://www.sofmap.com/search_result.aspx"
    query_param_name = "keyword"
    result = build_search_url(
        base_url=base_url,
        search_query=argp.search_query,
        query_param_name=query_param_name,
        query_encode_type=SHIFT_JIS,
    )
    print(result)


if __name__ == "__main__":
    main(sys.argv)
