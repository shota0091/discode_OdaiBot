from Repository.OdaiRepository import OdaiRepository
from Repository.ScheduleRepository import ScheduleRepository
from Service.NotifyServiceImpl import NotifyServiceImpl
from Service.RegisterServiceImpl import RegisterServiceImpl
from Service.ScheduleServiceImpl import ScheduleServiceImpl
from Util.GuildDataPathResolver import GuildDataPathResolver

class OdaiFactory:

  def __init__(self, guild_id: int):
    odai_json_path = GuildDataPathResolver.get_odaijson_path(guild_id)
    schedule_json_path = GuildDataPathResolver.get_schedulejson_path(guild_id)
    image_dir = GuildDataPathResolver.get_image_dir(guild_id)

    odaiRepository = OdaiRepository(odai_json_path)
    scheduleRepository = ScheduleRepository(schedule_json_path)

    self.odaiRepository = odaiRepository
    self.scheduleRepository = scheduleRepository
    self.registerService = RegisterServiceImpl(odaiRepository, image_dir)
    self.notifyService = NotifyServiceImpl(odaiRepository, image_dir)
    self.scheduleService = ScheduleServiceImpl(guild_id, scheduleRepository, self.notifyService)

  def getOdaiRepository(self):
    return self.odaiRepository

  def getscheduleRepository(self):
    return self.scheduleRepository
  
  def getRegisterService(self):
    return self.registerService
  
  def getNotifyService(self):
    return self.notifyService
  
  def getScheduleService(self):
    return self.scheduleService
