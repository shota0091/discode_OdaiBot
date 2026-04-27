from abc import ABC, abstractmethod

# 通知機能のインターフェイス
class NotifyServiceInterface(ABC):
    @abstractmethod
    async def send_notify_odai(self, channel, schedule: dict | None = None):
        pass
