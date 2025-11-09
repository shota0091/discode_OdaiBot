import os, random
from Interface.NotifyServiceInterface import NotifyServiceInterface
from Repository.OdaiRepository import OdaiRepository

class NotifyServiceImpl(NotifyServiceInterface):
    def __init__(self, odaiRepository: OdaiRepository, image_dir: str):
        self.repo = odaiRepository  # ✅名前統一
        self.image_dir = image_dir

    def sendNotifyOdai(self) -> str:
        odai_list = self.repo.load()

        # 未使用のお題を取得
        unused_list = [o for o in odai_list if not o.get("used", False)]

        # 全て使ったらリセット
        if not unused_list:
            for o in odai_list:
                o["used"] = False
            self.repo.save(odai_list)
            unused_list = odai_list

        # ランダム選択 & used=True
        odai = random.choice(unused_list)
        odai["used"] = True
        self.repo.save(odai_list)

        filename = odai["file"]
        return os.path.join(self.image_dir, filename)
