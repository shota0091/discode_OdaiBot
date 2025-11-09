from dataclasses import dataclass

@dataclass
class ScheduleEntity:
    channel_id: int
    time: str