from abc import ABC, abstractmethod
from .notification import LogUpdateNotification, URLNotification
from .command import LogUpdateNotificationGetCommand, URLNotificationGetCommand


class ILogUpdateNotificationRepository(ABC):
    @abstractmethod
    async def save_all(self, update_entries: list[LogUpdateNotification]):
        pass

    @abstractmethod
    async def get(
        self, command: LogUpdateNotificationGetCommand
    ) -> list[LogUpdateNotification]:
        pass


class IURLNotificationRepository(ABC):
    @abstractmethod
    async def save_all(self, url_entries: list[URLNotification]):
        pass

    @abstractmethod
    async def get(
        self,
        command: URLNotificationGetCommand,
    ) -> list[URLNotification]:
        pass
