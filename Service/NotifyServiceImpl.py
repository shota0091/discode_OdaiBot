import os
import random
from Service.Interface.NotifyServiceInterface import NotifyServiceInterface
from Repository.OdaiRepository import OdaiRepository

"""
お題送信処理クラス
"""
class NotifyServiceImpl(NotifyServiceInterface):
    """
    コンストラクタ
    Args:
        repository (OdaiRepository): JSONデータ操作クラス
        image_dir (str): お題画像ディレクトリ
    """
    def __init__(self, repository: OdaiRepository, image_dir: str):

        self.repository = repository
        self.image_dir = image_dir

    """
    未使用のお題をランダム取得し、使用済みにセット
    Returns:
        str: お題画像パス
    """
    def sendNotifyOdai(self) -> str:
        odai_list = self.repository.loadAll()
        unused_list = [o for o in odai_list if not o.used]

        # 全て使ったらリセット
        if not unused_list:
            for o in odai_list:
                o.used = False
            unused_list = odai_list

        selected = random.choice(unused_list)

        # フラグ更新
        for o in odai_list:
            if o.file == selected.file:
                o.used = True
                break

        self.repository.saveAll(odai_list)

        return os.path.join(self.image_dir, selected.file)
