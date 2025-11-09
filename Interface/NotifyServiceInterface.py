from abc import ABC, abstractmethod

# 通知機能のインターフェイス
class NotifyServiceInterface(ABC):
    @abstractmethod
    def sendNotifyOdai(self) -> str:
        pass
