import asyncio
import sys
import argparse
import uuid

import structlog

from common import logger_config
from databases.sqldb.pricelog import repository as p_repo
from domain.models.pricelog import pricelog as m_pricelog
from domain.models.notification import notification as m_noti
from databases.sqldb import util as db_util
from app.update.update_urls import (
    UpdateFuncType,
    UpdateNotificationResult,
    inactive_all_urls,
    inactive_file_urls,
    register_all_urls,
    register_new_urls,
    register_file_urls,
)


def set_argparse(argv):
    parser = argparse.ArgumentParser(
        description="URLをアップデート対象に登録します。既に対象のものは--allや--fileで指定しない限り変更しません。"
    )
    order_group = parser.add_mutually_exclusive_group(
        required=True
    )  # どちらか一方は必須
    order_group.add_argument(
        "--add",
        action="store_true",
        help="URLをアップデート対象に登録します。",
    )
    order_group.add_argument(
        "--remove",
        action="store_true",
        help="URLをアップデート対象から外します。",
    )

    target_group = parser.add_mutually_exclusive_group(required=True)
    target_group.add_argument(
        "--new",
        action="store_true",
        help="未登録のURLを対象にします。removeオプションと同時には使用できません。",
    )
    target_group.add_argument(
        "--all",
        action="store_true",
        help="すべてのURLを対象にします。",
    )
    target_group.add_argument(
        "-f",
        "--file",
        type=str,
        dest="file_path",  # args.file_path に格納される
        help="ファイルのURLを対象にします。\n"
        "URLリストが記述されたテキストファイルのパスを指定します。\n"
        "ファイルは1行に1つのURLを記述してください。\n"
        f"例: python {__file__} -f urls.txt",
    )

    return parser.parse_args(argv)


def create_result_message(result: UpdateNotificationResult) -> str:
    if result.update_type == UpdateFuncType.REMOVE.name:
        msg = "以下のURLを全てUpdate対象から外しました。\n"
    else:
        msg = "以下のURLを全てUpdate対象にしました。\n"
    for url in result.updated_list:
        msg = msg + f"{url.id} : {url.url}\n"

    if result.unregistered_list:
        msg = msg + "\n以下のURLは未登録です。\n"
        for url in result.unregistered_list:
            msg += f"{url}\n"

    if not result.added_list:
        return msg
    msg = msg + "\n以下のURLを新規に追加しました。\n"
    for url in result.added_list:
        msg = msg + f"{url.id} : {url.url}\n"
    return msg


async def main(argv):
    logger_config.configure_logger()
    run_id = str(uuid.uuid4())
    log = structlog.get_logger(__name__).bind(
        run_id=run_id, process_type="register_for_updates"
    )

    argp = set_argparse(argv[1:])
    if argp.remove and argp.new:
        log.error("invalid option combination. remove and new.")
        return
    db_util.create_db_and_tables()
    async for ses in db_util.get_async_session():
        if argp.file_path:
            with open(argp.file_path, "r") as f:
                target_urls = [
                    line.strip()
                    for line in f
                    if line.strip() and not line.strip().startswith("#")
                ]
                if not target_urls:
                    log.error(
                        f"No valid URLs in the file",
                        file_path=argp.file_path,
                    )
                    return
            if argp.add:
                result = await register_file_urls(ses=ses, target_urls=target_urls)
                log.info(
                    create_result_message(result),
                    order_type="add",
                    target="file",
                    file_path=argp.file_path,
                )
                return
            if argp.remove:
                result = await inactive_file_urls(ses=ses, target_urls=target_urls)
                log.info(
                    create_result_message(result),
                    order_type="remove",
                    target="file",
                    file_path=argp.file_path,
                )
                return
            return
        else:
            urlrepo = p_repo.URLRepository(ses=ses)
            target_db_urls = await urlrepo.get_all()
            if not target_db_urls:
                log.error("not exist urls in database")
                return
            if argp.remove and argp.all:
                result = await inactive_all_urls(ses=ses, target_urls=target_db_urls)
                log.info(
                    create_result_message(result), order_type="remove", target="all"
                )
                return
            if argp.add and argp.all:
                result = await register_all_urls(ses=ses, target_urls=target_db_urls)
                log.info(create_result_message(result), order_type="add", target="all")
                return
            if argp.add and argp.new:
                result = await register_new_urls(ses=ses, target_urls=target_db_urls)
                log.info(create_result_message(result), order_type="add", target="new")
                return


if __name__ == "__main__":
    asyncio.run(main(sys.argv))
