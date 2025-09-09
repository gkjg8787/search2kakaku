from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from domain.models.notification import (
    repository as m_repository,
    notification as m_notif,
    command as m_command,
)


class URLNotificationRepository(m_repository.IURLNotificationRepository):
    session: AsyncSession

    def __init__(self, ses: AsyncSession):
        self.session = ses

    async def save_all(self, url_entries: list[m_notif.URLNotification]):
        ses = self.session
        new_entries: list[m_notif.URLNotification] = []
        existing_entries_to_update: list[m_notif.URLNotification] = []
        for url_entry in url_entries:
            if not url_entry.id:
                db_urlnoti = await self._get_by_url_id(url_id=url_entry.url_id)
                if not db_urlnoti:
                    ses.add(url_entry)
                    await ses.flush()
                    new_entries.append(url_entry)
                    continue
                else:
                    is_update = await self._update(
                        db_urlnoti=db_urlnoti, update=url_entry
                    )
                    if is_update:
                        existing_entries_to_update.append(db_urlnoti)
                    continue
            else:
                db_urlnoti: m_notif.URLNotification = await ses.get(
                    m_notif.URLNotification, url_entry.id
                )
                if not db_urlnoti:
                    raise ValueError(f"not found url_entry.id, {url_entry.id}")
                is_update = await self._update(db_urlnoti=db_urlnoti, update=url_entry)
                if is_update:
                    existing_entries_to_update.append(url_entry)
        await ses.commit()
        for url_entry in new_entries:
            await ses.refresh(url_entry)
        for url_entry in existing_entries_to_update:
            await ses.refresh(url_entry)

    async def _update(
        self,
        db_urlnoti: m_notif.URLNotification,
        update: m_notif.URLNotification,
    ):
        if db_urlnoti.is_active == update.is_active:
            return False
        db_urlnoti.is_active = update.is_active
        return True

    async def _get_by_url_id(self, url_id: int) -> m_notif.URLNotification | None:
        result = await self.session.execute(
            select(m_notif.URLNotification).where(
                m_notif.URLNotification.url_id == url_id
            )
        )
        return result.scalar_one_or_none()

    async def get(
        self, command: m_command.URLNotificationGetCommand
    ) -> list[m_notif.URLNotification]:
        if command.url_id:
            db_urlnoti = await self._get_by_url_id(url_id=command.url_id)
            if not db_urlnoti:
                return []
            return [db_urlnoti]
        if command.is_active is not None:
            result = await self.session.execute(
                select(m_notif.URLNotification).where(
                    m_notif.URLNotification.is_active == command.is_active
                )
            )
            db_urlnotis = result.scalars()
            if db_urlnotis:
                return db_urlnotis.all()
        return []


class URLUpdateParameterRepository(m_repository.IURLUpdateParameterRepository):
    session: AsyncSession

    def __init__(self, ses: AsyncSession):
        self.session = ses

    async def save_all(self, url_entries: list[m_notif.URLUpdateParameter]):
        ses = self.session
        new_entries: list[m_notif.URLUpdateParameter] = []
        existing_entries_to_update: list[m_notif.URLUpdateParameter] = []
        for url_entry in url_entries:
            if not url_entry.id:
                db_urlparam = await self._get_by_url_id(url_id=url_entry.url_id)
                if not db_urlparam:
                    ses.add(url_entry)
                    await ses.flush()
                    new_entries.append(url_entry)
                    continue
                else:
                    is_update = await self._update(
                        db_urlparam=db_urlparam, update=url_entry
                    )
                    if is_update:
                        existing_entries_to_update.append(db_urlparam)
                    continue
            else:
                db_urlparam: m_notif.URLUpdateParameter = await ses.get(
                    m_notif.URLUpdateParameter, url_entry.id
                )
                if not db_urlparam:
                    raise ValueError(f"not found url_entry.id, {url_entry.id}")
                is_update = await self._update(
                    db_urlparam=db_urlparam, update=url_entry
                )
                if is_update:
                    existing_entries_to_update.append(url_entry)
        await ses.commit()
        for url_entry in new_entries:
            await ses.refresh(url_entry)
        for url_entry in existing_entries_to_update:
            await ses.refresh(url_entry)

    async def _update(
        self,
        db_urlparam: m_notif.URLUpdateParameter,
        update: m_notif.URLUpdateParameter,
    ):
        is_updated = False
        if db_urlparam.sitename != update.sitename:
            db_urlparam.sitename = update.sitename
            is_updated = True
        if db_urlparam.meta != update.meta:
            db_urlparam.meta = update.meta
            is_updated = True
        return is_updated

    async def _get_by_url_id(self, url_id: int) -> m_notif.URLUpdateParameter | None:
        result = await self.session.execute(
            select(m_notif.URLUpdateParameter).where(
                m_notif.URLUpdateParameter.url_id == url_id
            )
        )
        return result.scalar_one_or_none()

    async def get(
        self, command: m_command.URLUpdateParameterGetCommand
    ) -> list[m_notif.URLUpdateParameter]:
        if command.url_id:
            db_urlparam = await self._get_by_url_id(url_id=command.url_id)
            if not db_urlparam:
                return []
            return [db_urlparam]

        stmt = select(m_notif.URLUpdateParameter)
        if command.sitename:
            stmt = stmt.where(m_notif.URLUpdateParameter.sitename == command.sitename)

        result = await self.session.execute(stmt)
        db_urlparams = result.scalars()
        if db_urlparams:
            return db_urlparams.all()
        return []
