import os
from Interface.RegisterServiceInterface import RegisterServiceInterface
from Repository.OdaiRepository import OdaiRepository
from Entity.OdaiEntity import OdaiEntity

class RegisterServiceImpl(RegisterServiceInterface):
    def __init__(self, repository: OdaiRepository, image_dir: str, max_count: int = 50):
        self.repo = repository
        self.image_dir = image_dir  # ✅ repoではなくservice側が持つ
        self.max_count = max_count

    def add_odai(self, filename: str, content: bytes):
        # 同名チェック
        if self.repo.file_exists(filename):
            return False, f"❌ 同名ファイルが既に存在します：{filename}"

        # 上限チェック
        odai_list = self.repo.load()
        if len(odai_list) >= self.max_count:
            return False, f"⚠️ 登録数が上限({self.max_count})に達しています"

        # ✅ 画像保存：repoではなくserviceのimage_dirを使う
        save_path = os.path.join(self.image_dir, filename)
        with open(save_path, "wb") as f:
            f.write(content)

        # JSON登録
        odai_list.append(OdaiEntity(file=filename).__dict__)
        self.repo.save(odai_list)

        return True, f"お題を登録しました：{filename}"

    def remove_odai(self, filename: str) -> str:
        odai_list = self.repo.load()
        new_list = [o for o in odai_list if o.get("file") != filename]

        if len(new_list) == len(odai_list):
            return f"⚠️ {filename} は登録されていません"

        self.repo.save(new_list)

        # ✅ 画像削除
        try:
            os.remove(os.path.join(self.image_dir, filename))
        except FileNotFoundError:
            pass

        return f"🗑️ {filename} を削除しました（再登録可能）"
