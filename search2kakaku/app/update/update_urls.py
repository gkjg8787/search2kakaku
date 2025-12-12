from enum import Enum, auto
from typing import NamedTuple
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from domain.models.pricelog import pricelog as m_pricelog, command as p_command
from domain.models.notification import notification as m_noti, command as nofi_cmd
from domain.schemas.schemas import UpdateNotificationResult
from databases.sql.pricelog import repository as p_repo
from databases.sql.notification import repository as n_repo


class UpdateFuncType(Enum):
    ADD = auto()
    REMOVE = auto()


class RegisterURLByURL(NamedTuple):
    url: str
    sitename: str = ""
    options: dict = {}


class RegisterURLByID(NamedTuple):
    url_id: int
    sitename: str = ""
    options: dict = {}


def convert_to_urlnotification(
    data_list: list[m_pricelog.URL], is_active: bool = True
) -> list[m_noti.URLNotification]:
    results: list[m_noti.URLNotification] = []

    for url in data_list:
        urlnoti = m_noti.URLNotification(url_id=url.id, is_active=is_active)
        results.append(urlnoti)
    return results


async def get_target_db_urls(ses: AsyncSession) -> list[m_pricelog.URL]:
    urlrepo = p_repo.URLRepository(ses=ses)
    return await urlrepo.get_all()


async def inactive_all_urls(ses, target_urls: list[m_pricelog.URL]):
    urlnotirepo = n_repo.URLNotificationRepository(ses=ses)
    urlnoti_list = convert_to_urlnotification(data_list=target_urls, is_active=False)
    await urlnotirepo.save_all(url_entries=urlnoti_list)

    for url in target_urls:
        await ses.refresh(url)
    return UpdateNotificationResult(
        update_type=UpdateFuncType.REMOVE.name, updated_list=target_urls
    )


async def register_all_urls(ses, target_urls: list[m_pricelog.URL]):
    urlnotirepo = n_repo.URLNotificationRepository(ses=ses)
    urlnoti_list = convert_to_urlnotification(data_list=target_urls, is_active=True)
    await urlnotirepo.save_all(url_entries=urlnoti_list)

    for url in target_urls:
        await ses.refresh(url)
    return UpdateNotificationResult(
        update_type=UpdateFuncType.ADD.name, updated_list=target_urls
    )


async def register_new_urls(ses, target_urls: list[m_pricelog.URL]):
    urlnotirepo = n_repo.URLNotificationRepository(ses=ses)
    results: list[m_noti.URLNotification] = []
    results_for_msg: list[m_pricelog.URL] = []

    for url in target_urls:
        urlnoti = await urlnotirepo.get(
            command=nofi_cmd.URLNotificationGetCommand(url_id=url.id)
        )
        if urlnoti:
            continue
        urlnoti = m_noti.URLNotification(url_id=url.id, is_active=True)
        results.append(urlnoti)
        results_for_msg.append(url)
    await urlnotirepo.save_all(url_entries=results)

    for url in results_for_msg:
        await ses.refresh(url)
    return UpdateNotificationResult(
        update_type=UpdateFuncType.ADD.name, updated_list=results_for_msg
    )


async def register_urls(ses, target_urls: list[RegisterURLByURL]):
    urlnotirepo = n_repo.URLNotificationRepository(ses=ses)
    urlrepo = p_repo.URLRepository(ses=ses)
    added_urls_for_msg: list[m_pricelog.URL] = []
    add_and_update_notis_for_msg: list[m_pricelog.URL] = []
    for target in target_urls:
        db_url = await urlrepo.get(command=p_command.URLGetCommand(url=target.url))
        if not db_url:
            await urlrepo.save_all([m_pricelog.URL(url=target.url)])
            db_url = await urlrepo.get(command=p_command.URLGetCommand(url=target.url))
            added_urls_for_msg.append(db_url)

        db_urlnoti = await urlnotirepo.get(
            command=nofi_cmd.URLNotificationGetCommand(url_id=db_url.id)
        )
        if not db_urlnoti:
            await urlnotirepo.save_all(
                [m_noti.URLNotification(url_id=db_url.id, is_active=True)]
            )
            add_and_update_notis_for_msg.append(db_url)
        elif not db_urlnoti[0].is_active:
            db_urlnoti[0].is_active = True
            await urlnotirepo.save_all([db_urlnoti[0]])
            add_and_update_notis_for_msg.append(db_url)

        if target.sitename or target.options:
            await ses.refresh(db_url)
            await register_url_option_by_id(
                ses=ses,
                url_id=db_url.id,
                sitename=target.sitename,
                options=target.options,
            )

    for url in add_and_update_notis_for_msg:
        await ses.refresh(url)
    for url in added_urls_for_msg:
        await ses.refresh(url)
    return UpdateNotificationResult(
        update_type=UpdateFuncType.ADD.name,
        updated_list=add_and_update_notis_for_msg,
        added_list=added_urls_for_msg,
    )


async def register_one_url(ses, target_url: RegisterURLByURL):
    return await register_urls(ses=ses, target_urls=[target_url])


async def register_url_by_id(ses, target: RegisterURLByID):
    urlrepo = p_repo.URLRepository(ses=ses)
    db_url = await urlrepo.get(command=p_command.URLGetCommand(id=target.url_id))
    if not db_url:
        return UpdateNotificationResult(
            update_type=UpdateFuncType.ADD.name,
            unregistered_list=[f"url_id:{target.url_id}"],
        )
    return await register_urls(
        ses=ses,
        target_urls=[
            RegisterURLByURL(
                url=db_url.url, sitename=target.sitename, options=target.options
            )
        ],
    )


async def update_registered_urls(
    ses: AsyncSession, targets: list[RegisterURLByID | RegisterURLByURL]
):
    urlrepo = p_repo.URLRepository(ses=ses)
    add_and_update_notis_for_msg: list[m_pricelog.URL] = []
    added_urls_for_msg: list[m_pricelog.URL] = []
    unregistered_list: list[str] = []

    for target in targets:
        if isinstance(target, RegisterURLByURL):
            command = p_command.URLGetCommand(url=target.url)
        else:
            command = p_command.URLGetCommand(id=target.url_id)
        db_url = await urlrepo.get(command=command)
        if not db_url:
            if isinstance(target, RegisterURLByURL):
                unregistered_list.append(f"url:{target.url}")
            else:
                unregistered_list.append(f"url_id:{target.url_id}")
            continue

        # Reuse register_urls logic for notification and options
        result = await register_urls(
            ses=ses,
            target_urls=[
                RegisterURLByURL(
                    url=db_url.url, sitename=target.sitename, options=target.options
                )
            ],
        )
        add_and_update_notis_for_msg.extend(result.updated_list)
        added_urls_for_msg.extend(result.added_list)
        unregistered_list.extend(result.unregistered_list)

    return UpdateNotificationResult(
        update_type=UpdateFuncType.ADD.name,
        updated_list=add_and_update_notis_for_msg,
        added_list=added_urls_for_msg,
        unregistered_list=unregistered_list,
    )


async def register_url_by_id(ses, target: RegisterURLByID):
    urlrepo = p_repo.URLRepository(ses=ses)
    db_url = await urlrepo.get(command=p_command.URLGetCommand(id=target.url_id))
    if not db_url:
        return UpdateNotificationResult(
            update_type=UpdateFuncType.ADD.name,
            unregistered_list=[f"url_id:{target.url_id}"],
        )
    return await register_urls(
        ses=ses,
        target_urls=[
            RegisterURLByURL(
                url=db_url.url, sitename=target.sitename, options=target.options
            )
        ],
    )


async def register_url_option(ses, url: str, sitename: str, options: dict):
    urlrepo = p_repo.URLRepository(ses=ses)
    db_url = await urlrepo.get(command=p_command.URLGetCommand(url=url))
    if not db_url:
        return False
    return await register_url_option_by_id(
        ses=ses, url_id=db_url.id, sitename=sitename, options=options
    )


async def register_url_option_by_id(ses, url_id: int, sitename: str, options: dict):
    urloptrepo = n_repo.URLUpdateParameterRepository(ses=ses)
    db_urlopt = await urloptrepo.get(
        command=nofi_cmd.URLUpdateParameterGetCommand(url_id=url_id)
    )
    if db_urlopt:
        db_urlopt[0].sitename = sitename
        db_urlopt[0].meta = options
        await urloptrepo.save_all([db_urlopt[0]])
        return True

    urloption = m_noti.URLUpdateParameter(
        url_id=url_id, sitename=sitename, meta=options
    )
    await urloptrepo.save_all([urloption])
    return True


async def inactive_file_urls(ses, target_urls: list[str]):
    urlnotirepo = n_repo.URLNotificationRepository(ses=ses)
    urlrepo = p_repo.URLRepository(ses=ses)
    updates_for_msg: list[m_pricelog.URL] = []
    notfound_urls_for_msg: list[str] = []

    for target_url in target_urls:
        db_url = await urlrepo.get(command=p_command.URLGetCommand(url=target_url))
        if not db_url:
            notfound_urls_for_msg.append(target_url)
            continue
        db_urlnoti = await urlnotirepo.get(
            command=nofi_cmd.URLNotificationGetCommand(url_id=db_url.id)
        )
        if not db_urlnoti:
            continue
        if not db_urlnoti[0].is_active:
            continue
        db_urlnoti[0].is_active = False
        await urlnotirepo.save_all([db_urlnoti[0]])
        updates_for_msg.append(db_url)

    for url in updates_for_msg:
        await ses.refresh(url)
    return UpdateNotificationResult(
        update_type=UpdateFuncType.REMOVE.name,
        updated_list=updates_for_msg,
        unregistered_list=notfound_urls_for_msg,
    )


async def inactive_url(ses, target_url: str):
    return await inactive_file_urls(ses=ses, target_urls=[target_url])


async def inactive_url_by_id(ses, url_id: int):
    urlrepo = p_repo.URLRepository(ses=ses)
    db_url = await urlrepo.get(command=p_command.URLGetCommand(id=url_id))
    if not db_url:
        return UpdateNotificationResult(
            update_type=UpdateFuncType.REMOVE.name,
            unregistered_list=[f"url_id:{url_id}"],
        )
    return await inactive_file_urls(ses=ses, target_urls=[db_url.url])


async def inactive_urls(ses: AsyncSession, target_urls: list[int | str]):
    urlrepo = p_repo.URLRepository(ses=ses)
    updates_for_msg: list[m_pricelog.URL] = []
    notfound_urls_for_msg: list[str] = []

    for target in target_urls:
        if isinstance(target, str):
            command = p_command.URLGetCommand(url=target)
        else:
            command = p_command.URLGetCommand(id=target)
        db_url = await urlrepo.get(command=command)
        if not db_url:
            if isinstance(target, str):
                notfound_urls_for_msg.append(f"url:{target}")
            else:
                notfound_urls_for_msg.append(f"url_id:{target}")
            continue

        # Reuse inactive_file_urls logic
        result = await inactive_file_urls(ses=ses, target_urls=[db_url.url])
        updates_for_msg.extend(result.updated_list)
        notfound_urls_for_msg.extend(result.unregistered_list)

    return UpdateNotificationResult(
        update_type=UpdateFuncType.REMOVE.name,
        updated_list=updates_for_msg,
        unregistered_list=notfound_urls_for_msg,
    )
