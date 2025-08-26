from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from domain.models.pricelog import pricelog as m_pricelog
from domain.models.notification import notification as m_noti


class ViewURLActive(BaseModel):
    id: int
    url: str
    is_active: bool | None = None


class ViewURLActiveGetCommand(BaseModel):
    id: int | None = None
    url: str | None = None
    is_active: bool | None = None
    excluding_none: bool = False


class ViewURLActiveRepository:
    session: AsyncSession

    def __init__(self, ses: AsyncSession):
        self.session = ses

    async def get(self, command: ViewURLActiveGetCommand) -> list[ViewURLActive]:
        ses = self.session
        stmt = (
            select(m_pricelog.URL, m_noti.URLNotification)
            .select_from(m_pricelog.URL)
            .outerjoin(
                m_noti.URLNotification,
                m_pricelog.URL.id == m_noti.URLNotification.url_id,
            )
        )
        if command.id:
            stmt = stmt.where(m_pricelog.URL.id == command.id)
        if command.url:
            stmt = stmt.where(m_pricelog.URL.url == command.url)
        if command.is_active is not None:
            if command.excluding_none == False:
                stmt = stmt.where(m_noti.URLNotification.is_active == command.is_active)
            else:
                stmt = stmt.where(
                    or_(
                        m_noti.URLNotification.is_active.is_(None),
                        m_noti.URLNotification.is_active == False,
                    )
                )
        db = await ses.execute(stmt)
        results = db.all()
        if not results:
            return []
        return self._convert_db_to_viewurlactives(results)

    def _convert_db_to_viewurlactives(self, results) -> list[ViewURLActive]:
        new_results = []
        for r in results:
            for rr in r:
                if isinstance(rr, m_pricelog.URL):
                    db_url = rr
                    continue
                if isinstance(rr, m_noti.URLNotification):
                    db_noti = rr
                    continue
                else:
                    db_noti = None
                    continue
            if db_url and db_noti:
                new_results.append(
                    ViewURLActive(
                        id=db_url.id, url=db_url.url, is_active=db_noti.is_active
                    )
                )
                continue
            if db_url and not db_noti:
                new_results.append(
                    ViewURLActive(id=db_url.id, url=db_url.url, is_active=False)
                )
                continue

            ValueError("convert error. URL is None.")
        return new_results
