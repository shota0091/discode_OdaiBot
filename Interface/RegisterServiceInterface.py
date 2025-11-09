from abc import ABC, abstractmethod

# 登録用のインターフェイス
class RegisterServiceInterface(ABC):
    @abstractmethod
    def add_odai(self, filename: str) -> str:
        pass

    @abstractmethod
    def remove_odai(self, filename: str) -> str:
        pass