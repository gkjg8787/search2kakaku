from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from domain.models.notification import (
    repository as m_repository,
    notification as m_notif,
    command as m_command,
)


class LogUpdateNotificationRepository(m_repository.ILogUpdateNotificationRepository):
    session: AsyncSession

    def __init__(self, ses: AsyncSession):
        self.session = ses

    async def save_all(self, update_entries: list[m_notif.LogUpdateNotification]):
        ses = self.session
        for update_entry in update_entries:
            if not update_entry.id:
                ses.add(update_entry)
                continue
            db_noti: m_notif.LogUpdateNotification = await ses.get(
                m_notif.LogUpdateNotification, update_entry.id
            )

            if not db_noti:
                raise ValueError(f"not found update_entry.id ,{update_entry.id}")
            db_noti.current_state = update_entry.current_state
            db_noti.notification_type = update_entry.notification_type
            db_noti.range_type = update_entry.range_type
            db_noti.error_msg = update_entry.error_msg
            db_noti.meta = update_entry.meta
            db_noti.retry_count = update_entry.retry_count
            continue

        await ses.commit()
        for update_entry in update_entries:
            await ses.refresh(update_entry)
        return

    async def get(
        self, command: m_command.LogUpdateNotificationGetCommand
    ) -> list[m_notif.LogUpdateNotification]:
        stmt = select(m_notif.LogUpdateNotification)
        if command.id:
            stmt = stmt.where(m_notif.LogUpdateNotification.id == command.id)
        if command.target_entity_id:
            stmt = stmt.where(
                m_notif.LogUpdateNotification.target_entity_id
                == command.target_entity_id
            )
        if command.target_entity_type:
            stmt = stmt.where(
                m_notif.LogUpdateNotification.target_entity_type
                == command.target_entity_type
            )
        if command.range_type:
            stmt = stmt.where(
                m_notif.LogUpdateNotification.range_type == command.range_type
            )
        if command.notification_type:
            stmt = stmt.where(
                m_notif.LogUpdateNotification.notification_type
                == command.notification_type
            )

        res = await self.session.execute(stmt)
        results = res.scalars()
        if not results:
            return []
        return results.all()


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
