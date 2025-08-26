from enum import Enum, auto

from pydantic import BaseModel, Field

from domain.models.pricelog import pricelog as m_pricelog, command as p_command
from domain.models.notification import notification as m_noti, command as nofi_cmd
from databases.sql.pricelog import repository as p_repo
from databases.sql.notification import repository as n_repo


class UpdateFuncType(Enum):
    ADD = auto()
    REMOVE = auto()


class UpdateNotificationResult(BaseModel):
    update_type: str = Field(default="")
    updated_list: list[m_pricelog.URL] = Field(default_factory=list)
    added_list: list[m_pricelog.URL] = Field(default_factory=list)
    unregistered_list: list[str] = Field(default_factory=list)


def convert_to_urlnotification(
    data_list: list[m_pricelog.URL], is_active: bool = True
) -> list[m_noti.URLNotification]:
    results: list[m_noti.URLNotification] = []

    for url in data_list:
        urlnoti = m_noti.URLNotification(url_id=url.id, is_active=is_active)
        results.append(urlnoti)
    return results


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
        if urlnoti and urlnoti[0].is_active:
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


async def register_file_urls(ses, target_urls: list[str]):
    urlnotirepo = n_repo.URLNotificationRepository(ses=ses)
    urlrepo = p_repo.URLRepository(ses=ses)
    added_urls_for_msg: list[m_pricelog.URL] = []
    add_and_update_notis_for_msg: list[m_pricelog.URL] = []
    for target_url in target_urls:
        db_url = await urlrepo.get(command=p_command.URLGetCommand(url=target_url))
        if not db_url:
            await urlrepo.save_all([m_pricelog.URL(url=target_url)])
            db_url = await urlrepo.get(command=p_command.URLGetCommand(url=target_url))
            added_urls_for_msg.append(db_url)
        db_urlnoti = await urlnotirepo.get(
            command=nofi_cmd.URLNotificationGetCommand(url_id=db_url.id)
        )
        if not db_urlnoti:
            await urlnotirepo.save_all(
                [m_noti.URLNotification(url_id=db_url.id, is_active=True)]
            )
            add_and_update_notis_for_msg.append(db_url)
            continue
        if not db_urlnoti[0].is_active:
            db_urlnoti[0].is_active = True
            await urlnotirepo.save_all([db_urlnoti[0]])
            add_and_update_notis_for_msg.append(db_url)
            continue

    for url in add_and_update_notis_for_msg:
        await ses.refresh(url)
    for url in added_urls_for_msg:
        await ses.refresh(url)
    return UpdateNotificationResult(
        update_type=UpdateFuncType.ADD.name,
        updated_list=add_and_update_notis_for_msg,
        added_list=added_urls_for_msg,
    )


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
