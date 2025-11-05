import json
import os
from Entity.OdaiEntity import OdaiEntity

"""
odaiBotの情報操作クラス
"""
class OdaiRepository:
  """
  コンストラクタ
  Args:
      jsonPath(str) : Jsonのパス
  """
  def __init__(self,jsonPath: str):
    self.jsonPath = jsonPath

  #Jsonデータを読み込んでodaiEntityに格納する
  def loadAll(self) -> list[OdaiEntity]:
    """
    お題の一覧取得クラス
    Returns:
        list[OdaiEntity]: お題一覧
    """
    # ファイルが存在しない場合は空のListを返す
    if not os.path.exists(self.jsonPath):
      return []
    #Jsonファイルの読み込み
    with open(self.jsonPath,"r",encoding="utf-8") as f:
      data = json.load(f)
    odaiList = data.get("odai_list", [])
    # 取得したJson情報をOdaiEntityに変換する
    return [OdaiEntity(**item) for item in odaiList]
  
  # お題情報をJsonに書き込む処理
  def saveAll(self,odaiEntities: list[OdaiEntity]):
    """
    お題の一覧取得クラス
    Args:
        odaiEntities (list[OdaiEntity]): 登録するお題ファイル名
    """
    
    # Jsonの作成
    data = {
      "odai_list": [vars(e) for e in odaiEntities]
    }
    # 古いJsonを新しいJsonに上書きする処理
    with open(self.jsonPath,"w",encoding="utf-8") as f:
      json.dump(data,f,ensure_ascii=False,indent=2)