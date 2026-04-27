from abc import ABC, abstractmethod

class ScheduleServiceInterface(ABC):
    
    @abstractmethod
    def save(self, channel_id: int, time: str) -> str:
        """
        スケジュール設定を保存する
        Returns: Discord表示用メッセージ
        """
        pass

    @abstractmethod
    async def run(self, bot) -> None:
        """
        現在時刻と一致するスケジュールがあれば実行する
        """
        pass