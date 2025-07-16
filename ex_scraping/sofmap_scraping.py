import sys
import asyncio
import argparse
import time

from databases.sqldb.util import get_async_session
from app.sofmap.web_scraper import scrape_and_save, ScrapeCommand


def set_argparse(argv):
    parser = argparse.ArgumentParser(
        description="複数のURLからデータを取得して処理します。"
    )
    group = parser.add_mutually_exclusive_group(required=True)  # どちらか一方は必須

    # 1. 位置引数で複数のURLを受け取るオプション
    group.add_argument(
        "urls",  # 位置引数として受け取る
        nargs="*",  # 0個以上の引数を受け取り、リストにする
        default=[],  # 引数が指定されなかった場合のデフォルト値
        help="直接処理するURLをスペース区切りで複数指定します。\n"
        f"例: python {__file__} https://example.com https://google.com",
    )

    # 2. ファイルからURL一覧を読み込むオプション
    group.add_argument(
        "-f",
        "--file",
        type=str,
        dest="file_path",  # args.file_path に格納される
        help="URLリストが記述されたテキストファイルのパスを指定します。\n"
        "ファイルは1行に1つのURLを記述してください。\n"
        f"例: python {__file__} -f urls.txt",
    )
    parser.add_argument(
        "--ucaa",
        action="store_true",
    )

    return parser.parse_args(argv[1:])


async def async_main(argv):
    argp = set_argparse(argv)
    if argp.urls:
        target_urls = argp.urls
        if not target_urls:
            print("エラー：URLがありません")
            return
    elif argp.file_path:
        try:
            with open(argp.file_path, "r", encoding="utf-8") as f:
                # 空行やコメント行（#で始まる行）をスキップ
                target_urls = [
                    line.strip()
                    for line in f
                    if line.strip() and not line.strip().startswith("#")
                ]
            if not target_urls:
                print(
                    f"エラー: 指定されたファイル '{argp.file_path}' に有効なURLが見つかりません。",
                    file=sys.stderr,
                )
                return
        except FileNotFoundError:
            print(
                f"エラー: 指定されたファイル '{argp.file_path}' が見つかりません。",
                file=sys.stderr,
            )
            return
        except Exception as e:
            print(
                f"エラー: ファイル '{argp.file_path}' の読み込み中に問題が発生しました: {e}",
                file=sys.stderr,
            )
            return

    async for ses in get_async_session():
        for url in target_urls:
            command = ScrapeCommand(url=url, async_session=ses, is_ucaa=argp.ucaa)
            await scrape_and_save(command=command)
            time.sleep(1)


def main(argv):
    asyncio.run(async_main(argv=argv))


if __name__ == "__main__":
    main(sys.argv)
