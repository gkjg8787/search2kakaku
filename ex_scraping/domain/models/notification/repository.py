from abc import ABC, abstractmethod
from .notification import URLNotification
from .command import URLNotificationGetCommand


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
