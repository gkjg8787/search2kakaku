from abc import ABC, abstractmethod
from .activitylog import ActivityLog
from .command import ActivityLogGetCommand


class IActivityLogRepository(ABC):
    @abstractmethod
    async def save_all(self, log_entries: list[ActivityLog]):
        pass

    @abstractmethod
    async def get(self, command: ActivityLogGetCommand) -> list[ActivityLog]:
        pass

    @abstractmethod
    async def get_activity_types(self) -> list[str]:
        pass

    @abstractmethod
    async def get_caller_types(self) -> list[str]:
        pass
