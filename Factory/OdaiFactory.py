import os
from Repository.OdaiRepository import OdaiRepository
from Service.NotifyServiceImpl import NotifyServiceImpl
from Service.RegisterServiceImpl import RegisterServiceImpl

"""
お題Bot Factoryクラス
"""
class OdaiFactory:
  _instance = None

  def __new__(cls, jsonPath,image_dir):
    if cls._instance is None:
      cls._instance = super().__new__(cls)

      repository = OdaiRepository(jsonPath)

      cls._instance.repository = repository 
      cls._instance.registerService = RegisterServiceImpl(repository)
      cls._instance.notifyService = NotifyServiceImpl(repository,image_dir)

    return cls._instance
  

  def getRepository(self):  # ← ✅ 追加
    return self.repository

  """
  RegisterService実行
  Returns:
            registerService: 登録実行クラス
  """
  def getRegisterService(self):
    return self.registerService
  
  """
  NotifyService実行
  Returns:
            NotifyService: 通知実行クラス
  """
  def getNotifyService(self):
    return self.notifyService
