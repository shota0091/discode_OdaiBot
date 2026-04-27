from Repository.MySQLDatabase import MySQLDatabase
from Repository.OdaiRepository import OdaiRepository
from Repository.ScheduleRepository import ScheduleRepository
from Repository.UserRepository import UserRepository
from Repository.InviteRepository import InviteRepository
from Service.NotifyServiceImpl import NotifyServiceImpl
from Service.ScheduleServiceImpl import ScheduleServiceImpl

class OdaiFactory:

    _db = None

    def __init__(self, guild_id: int):
        if OdaiFactory._db is None:
            OdaiFactory._db = MySQLDatabase()

        self.db = OdaiFactory._db

        self.odaiRepository = OdaiRepository(self.db)
        self.scheduleRepository = ScheduleRepository(self.db)
        self.userRepository = UserRepository(self.db)
        self.inviteRepository = InviteRepository(self.db)
        self.notifyService = NotifyServiceImpl(self.odaiRepository, self.db)
        self.scheduleService = ScheduleServiceImpl(
            guild_id,
            self.scheduleRepository,
            self.notifyService,
        )

    def getOdaiRepository(self):
        return self.odaiRepository

    def getNotifyService(self):
        return self.notifyService

    def getScheduleService(self):
        return self.scheduleService

    def getUserRepository(self):
        return self.userRepository

    def getInviteRepository(self):
        return self.inviteRepository
