from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from domain.models.pricelog import (
    repository as m_repository,
    pricelog as m_pricelog,
    command as m_command,
)


class PriceLogRepository(m_repository.IPriceLogRepository):
    session: AsyncSession

    def __init__(self, ses: AsyncSession):
        self.session = ses

    async def save_all(self, pricelog_entries: list[m_pricelog.PriceLog]):
        ses = self.session
        for pricelog in pricelog_entries:
            if not pricelog.url_id:
                result = await ses.execute(
                    select(m_pricelog.URL).where(m_pricelog.URL.url == pricelog.url.url)
                )
                url = result.scalar()
                if url:
                    pricelog.url = url
            if not pricelog.shop_id:
                result = await ses.execute(
                    select(m_pricelog.Shop).where(
                        m_pricelog.Shop.name == pricelog.shop.name
                    )
                )
                shop = result.scalar()
                if shop:
                    pricelog.shop = shop
            ses.add(pricelog)
            await ses.flush()

        await ses.commit()
        for pricelog in pricelog_entries:
            await ses.refresh(pricelog)

    async def get(
        self, command: m_command.PriceLogGetCommand
    ) -> list[m_pricelog.PriceLog]:
        ses = self.session
        stmt = select(m_pricelog.PriceLog)
        if command.id:
            stmt = stmt.where(m_pricelog.PriceLog.id == command.id)
        if command.url:
            stmt = stmt.where(m_pricelog.PriceLog.url.url == command.url)
        if command.start_utc_date:
            stmt = stmt.where(m_pricelog.PriceLog.created_at >= command.start_utc_date)
        if command.end_utc_date:
            stmt = stmt.where(m_pricelog.PriceLog.created_at <= command.end_utc_date)
        ret = await ses.execute(stmt)
        results = ret.scalars()
        if not results:
            return []
        return results.all()


class URLRepository(m_repository.IURLRepository):
    session: AsyncSession

    def __init__(self, ses: AsyncSession):
        self.session = ses

    async def save_all(self, url_entries: list[m_pricelog.URL]):
        ses = self.session
        adds = []
        for url in url_entries:
            if not url.id:
                result = await ses.execute(
                    select(m_pricelog.URL).where(m_pricelog.URL.url == url.url)
                )
                db_url = result.scalar()
                if db_url:
                    continue
                ses.add(url)
                ses.flush()
                adds.append(url)
        await ses.commit()
        for url in adds:
            await ses.refresh(url)

    async def get_by_url(self, url_path: str) -> m_pricelog.URL | None:
        ses = self.session
        result = await ses.execute(
            select(m_pricelog.URL).where(m_pricelog.URL.url == url_path)
        )
        return result.scalar()


class ShopRepository(m_repository.IShopRepository):
    session: AsyncSession

    def __init__(self, ses: AsyncSession):
        self.session = ses

    async def save_all(self, shop_entries: list[m_pricelog.Shop]):
        ses = self.session
        adds = []
        for shop in shop_entries:
            result = await ses.execute(
                select(m_pricelog.Shop).where(m_pricelog.Shop.name == shop.name)
            )
            db_shop = result.scalar()
            if db_shop:
                continue
            ses.add(shop)
            ses.flush()
            adds.append(shop)
        await ses.commit()
        for shop in adds:
            await ses.refresh(shop)

    async def get_by_name(self, name: str) -> m_repository.Shop | None:
        ses = self.session
        result = await ses.execute(
            select(m_pricelog.Shop).where(m_pricelog.Shop.name == name)
        )
        return result.scalar()
