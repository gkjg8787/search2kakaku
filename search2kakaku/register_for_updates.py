import asyncio
import argparse
import uuid
import json
from urllib.parse import urlparse

import structlog

from common import logger_config
from databases.sql.pricelog import repository as p_repo
from domain.models.notification import notification as m_noti
from domain.schemas.schemas import UpdateNotificationResult
from databases.sql import util as db_util
from app.update import update_urls, view_urls
from app.gemini import models as gemini_models


class CommandOrder:
    ADD = "add"
    REMOVE = "remove"
    VIEW = "view"


class ViewTargetOrder:
    ALL = "all"
    ACTIVE = "active"
    INACTIVE = "inactive"


def set_argparse():
    parser = argparse.ArgumentParser(
        description="URLをアップデート対象かどうか変更します。"
    )
    subparsers = parser.add_subparsers(
        dest="command", help="利用可能なコマンド", required=True
    )
    add_opt_argparse(subparsers)
    remove_opt_argparse(subparsers)
    view_opt_argparse(subparsers)

    return parser.parse_args()


def add_opt_argparse(subparsers):
    add_parser = subparsers.add_parser(
        CommandOrder.ADD, help="URLをアップデート対象にします。"
    )
    add_target_group = add_parser.add_mutually_exclusive_group(required=True)
    add_target_group.add_argument(
        "--new",
        action="store_true",
        help="未登録のURLを対象にします。",
    )
    add_target_group.add_argument(
        "--all",
        action="store_true",
        help="すべてのURLを対象にします。",
    )
    add_target_group.add_argument(
        "-f",
        "--file",
        type=str,
        dest="file_path",  # args.file_path に格納される
        help="ファイルのURLを対象にします。\n"  # Note: The original had \n here, which is correct for a string literal representing a newline in Python.
        "URLリストが記述されたテキストファイルのパスを指定します。\n"
        "ファイルは1行に1つのURLを記述してください。\n"
        f"例: python {__file__} -f urls.txt",
    )
    add_target_group.add_argument(
        "--url",
        type=str,
        help="URLをアップデート対象にします。",
    )
    add_target_group.add_argument(
        "--url_id",
        type=int,
        help="URL_IDをアップデート対象にします。",
    )
    add_parser.add_argument(
        "--sitename",
        type=str,
        help="URLのサイト名を指定します。",
    )
    opt_group = add_parser.add_mutually_exclusive_group()
    opt_group.add_argument(
        "--options",
        type=str,
        help='URLのオプションをJSON形式で指定します。例: \'{"key": "value"}\'.',
    )
    opt_group.add_argument(
        "--options_from",
        type=str,
        help="URLのオプションを指定ファイルから読み出します。",
    )


def remove_opt_argparse(subparsers):
    remove_parser = subparsers.add_parser(
        CommandOrder.REMOVE, help="URLをアップデート対象から外します。"
    )
    remove_target_group = remove_parser.add_mutually_exclusive_group(required=True)
    remove_target_group.add_argument(
        "--all",
        action="store_true",
        help="すべてのURLを対象にします。",
    )
    remove_target_group.add_argument(
        "-f",
        "--file",
        type=str,
        dest="file_path",
        help="ファイルのURLを対象にします。\n"
        "URLリストが記述されたテキストファイルのパスを指定します。\n"
        "ファイルは1行に1つのURLを記述してください。\n"
        f"例: python {__file__} -f urls.txt",
    )
    remove_target_group.add_argument(
        "--url",
        type=str,
        help="URLをアップデート対象から外します。",
    )
    remove_target_group.add_argument(
        "--url_id",
        type=int,
        help="URL_IDをアップデート対象から外します。",
    )


def view_opt_argparse(subparsers):
    view_parser = subparsers.add_parser(
        CommandOrder.VIEW, help="URLのアップデート対象情報を表示します。"
    )
    VIEW_TARGET_LIST = [
        ViewTargetOrder.ALL,
        ViewTargetOrder.ACTIVE,
        ViewTargetOrder.INACTIVE,
    ]
    view_parser.add_argument(
        "--target",
        type=lambda s: str(s).lower(),
        choices=VIEW_TARGET_LIST,
        default=ViewTargetOrder.ALL,
        help=f"アップデート対象、対象外を表示:{",".join(VIEW_TARGET_LIST)}",
    )
    view_parser.add_argument(
        "--url_option",
        action="store_true",
        help="URLオプションを表示します。",
    )


def create_result_message(result: UpdateNotificationResult) -> str:
    if result.update_type == update_urls.UpdateFuncType.REMOVE.name:
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


def get_target_urls_in_file(file_path: str):
    with open(file_path, "r") as f:
        target_urls = [
            line.strip()
            for line in f
            if line.strip() and not line.strip().startswith("#")
        ]
        return target_urls
    return []


async def start_add_command(ses, argp, log):
    if argp.sitename:
        sitename = argp.sitename
    else:
        sitename = ""
    if argp.options:
        try:
            options = json.loads(argp.options)
            if not isinstance(options, dict):
                raise ValueError("options is not dict")
            gemini_models.AskGeminiOptions(**options)
        except Exception as e:
            log.error(
                f"Invalid JSON format for options",
                options=argp.options,
                error=f"type:{type(e).__name__}, {e}",
            )
            return
    elif argp.options_from:
        try:
            with open(argp.options_from, "r") as f:
                options = json.load(f)
            if not isinstance(options, dict):
                raise ValueError("options is not dict")
            gemini_models.AskGeminiOptions(**options)
        except Exception as e:
            log.error(
                f"Failed to read or parse options from file",
                file_path=argp.options_from,
                error=f"type:{type(e).__name__}, {e}",
            )
            return
    else:
        options = {}

    if argp.file_path:
        target_urls = get_target_urls_in_file(argp.file_path)
        if not target_urls:
            log.error(
                f"No valid URLs in the file",
                file_path=argp.file_path,
            )
            return

        target_url_infos = [
            update_urls.RegisterURLByURL(url=url, sitename=sitename, options=options)
            for url in target_urls
        ]
        result = await update_urls.register_urls(ses=ses, target_urls=target_url_infos)
        log.info(
            create_result_message(result),
            order_type="add",
            target="file",
            file_path=argp.file_path,
        )
        return
    elif argp.url:
        result = await update_urls.register_one_url(
            ses=ses,
            target_url=update_urls.RegisterURLByURL(
                url=argp.url, sitename=sitename, options=options
            ),
        )
        log.info(
            create_result_message(result),
            order_type="add",
            target="url",
            url=argp.url,
        )
        return
    elif argp.url_id:
        result = await update_urls.register_url_by_id(
            ses=ses,
            target=update_urls.RegisterURLByID(
                url_id=argp.url_id, sitename=sitename, options=options
            ),
        )
        log.info(
            create_result_message(result),
            order_type="add",
            target="url_id",
            url_id=argp.url_id,
        )
        return
    else:
        target_db_urls = await update_urls.get_target_db_urls(ses=ses)
        if not target_db_urls:
            log.error("not exist urls in database")
            return
        if argp.all:
            result = await update_urls.register_all_urls(
                ses=ses, target_urls=target_db_urls
            )
            log.info(
                create_result_message(result),
                order_type="add",
                target="all",
                count=len(target_db_urls),
            )
            return
        if argp.new:
            result = await update_urls.register_new_urls(
                ses=ses, target_urls=target_db_urls
            )
            log.info(create_result_message(result), order_type="add", target="new")
            return
        return


async def start_remove_command(ses, argp, log):
    if argp.file_path:
        target_urls = get_target_urls_in_file(argp.file_path)
        if not target_urls:
            log.error(
                f"No valid URLs in the file",
                file_path=argp.file_path,
            )
            return
        result = await update_urls.inactive_file_urls(ses=ses, target_urls=target_urls)
        log.info(
            create_result_message(result),
            order_type="remove",
            target="file",
            file_path=argp.file_path,
        )
        return
    elif argp.url:
        result = await update_urls.inactive_url(ses=ses, target_url=argp.url)
        log.info(
            create_result_message(result),
            order_type="remove",
            target="url",
            url=argp.url,
        )
        return
    elif argp.url_id:
        result = await update_urls.inactive_url_by_id(ses=ses, url_id=argp.url_id)
        log.info(
            create_result_message(result),
            order_type="remove",
            target="url_id",
            url_id=argp.url_id,
        )
        return
    else:
        target_db_urls = await update_urls.get_target_db_urls(ses=ses)
        if not target_db_urls:
            log.error("not exist urls in database")
            return
        if argp.all:
            result = await update_urls.inactive_all_urls(
                ses=ses, target_urls=target_db_urls
            )
            log.info(create_result_message(result), order_type="remove", target="all")
            return
        return


def create_view_result_message(result: list[view_urls.ViewURLActive]) -> str:
    if result:
        new_result: list = []
        for r in result:
            new_result.append(r.model_dump(exclude_none=True))
        return str(new_result)
    return "no results"


async def start_view_command(ses, argp, log):
    viewrepo = view_urls.ViewURLActiveRepository(ses=ses)

    match argp.target:
        case ViewTargetOrder.ALL:
            result = await viewrepo.get(
                command=view_urls.ViewURLActiveGetCommand(view_option=argp.url_option)
            )
            if result:
                log.info(create_view_result_message(result))
            return
        case ViewTargetOrder.ACTIVE:
            result = await viewrepo.get(
                command=view_urls.ViewURLActiveGetCommand(
                    is_active=True, view_option=argp.url_option
                )
            )
            log.info(create_view_result_message(result))
            return
        case ViewTargetOrder.INACTIVE:
            result = await viewrepo.get(
                command=view_urls.ViewURLActiveGetCommand(
                    is_active=False, excluding_none=True, view_option=argp.url_option
                )
            )
            log.info(create_view_result_message(result))
            return
    return


async def main():
    logger_config.configure_logger()
    run_id = str(uuid.uuid4())
    log = structlog.get_logger(__name__).bind(
        run_id=run_id, process_type="register_for_updates"
    )

    argp = set_argparse()
    log.info("parse params", args=argp)

    db_util.create_db_and_tables()
    async for ses in db_util.get_async_session():
        match argp.command:
            case CommandOrder.ADD:
                await start_add_command(ses=ses, argp=argp, log=log)
                return
            case CommandOrder.REMOVE:
                await start_remove_command(ses=ses, argp=argp, log=log)
                return
            case CommandOrder.VIEW:
                await start_view_command(ses=ses, argp=argp, log=log)
                return


if __name__ == "__main__":
    asyncio.run(main())
