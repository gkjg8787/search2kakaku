from abc import ABC, abstractmethod
from datetime import datetime
from .pricelog import PriceLog, URL, Shop
from .command import PriceLogGetCommand


class IPriceLogRepository(ABC):
    @abstractmethod
    async def save_all(self, pricelog_entries: list[PriceLog]):
        pass

    @abstractmethod
    async def get(self, command: PriceLogGetCommand) -> list[PriceLog]:
        pass


class IURLRepository(ABC):
    @abstractmethod
    async def save_all(self, url_entries: list[URL]):
        pass

    @abstractmethod
    async def get_by_url(self, url_path: str) -> URL:
        pass


class IShopRepository(ABC):
    @abstractmethod
    async def save_all(self, shop_entries: list[Shop]):
        pass

    @abstractmethod
    async def get_by_name(self, name: str) -> Shop:
        pass
