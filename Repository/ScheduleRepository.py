import json, os
from Entity.ScheduleEntity import ScheduleEntity
from Interface.BaseRepositoryInterface import BaseRepositoryInterface

class ScheduleRepository(BaseRepositoryInterface):
    def __init__(self, jsonPath: str):
        self.jsonPath = jsonPath

    def load(self) -> list[ScheduleEntity]:
        if not os.path.exists(self.jsonPath):
            return []
        with open(self.jsonPath, "r") as f:
            data = json.load(f)
        return [ScheduleEntity(**item) for item in data]

    def save(self, schedules: list[ScheduleEntity]):
        data = [s.__dict__ for s in schedules]
        with open(self.jsonPath, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
