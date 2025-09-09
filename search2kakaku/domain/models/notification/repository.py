from abc import ABC, abstractmethod
from .notification import URLNotification, URLUpdateParameter
from .command import URLNotificationGetCommand, URLUpdateParameterGetCommand


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


class IURLUpdateParameterRepository(ABC):
    @abstractmethod
    async def save_all(self, url_entries: list[URLUpdateParameter]):
        pass

    @abstractmethod
    async def get(
        self,
        command: URLUpdateParameterGetCommand,
    ) -> list[URLUpdateParameter]:
        pass
