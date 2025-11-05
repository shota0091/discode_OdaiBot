from Service.Interface.RegisterServiceInterface import RegisterServiceInterface
from Repository.OdaiRepository import OdaiRepository
from Entity.OdaiEntity import OdaiEntity

"""
お題登録・削除処理を行うクラス
"""
class RegisterServiceImpl(RegisterServiceInterface):
    """
    コンストラクタ
    Args:
        repository(OdaiRepository) : お題取得クラス
    """
    def __init__(self,repository : OdaiRepository, max_count: int = 365):
        self.repository = repository
        self.max_count = max_count

    """
    新しいお題を登録する
    Args:
        filename (str): 登録するお題ファイル名

    Returns:
        str: 処理結果メッセージ（成功/警告）
    """
    def add_odai(self, filename: str) -> str:

        # 1. 現在のお題一覧を取得
        odai_list = self.repository.loadAll()

        # 2.既に登録しているされているお題が登録されているかチェック
        if any(o.file == filename for o in odai_list):
            return f"{filename}は既に登録されています。"
        
        removed = None
        # 3.上限を超えたら古い順から削除する
        if len(odai_list) >= self.max_count:
            odai_list.sort(key=lambda o: o.added_at)
            removed = odai_list.pop(0)
        
        # 新しいお題の登録
        addNewOdai = OdaiEntity(file = filename)
        odai_list.append(addNewOdai)
        self.repository.saveAll(odai_list)

        #完了メッセージ
        if removed:
            return f"{removed.file}は登録上限({self.max_count}件)超えているため削除しました。¥n✅ {filename} を登録しました。"
        else:
            return f"✅ {filename} を登録しました。"
        
    """
    お題を削除する
    Args:
        filename (str): 登録するお題ファイル名

    Returns:
        str: 処理結果メッセージ（成功/警告）
    """
    def remove_odai(self, filename: str) -> str:

        # 1. 現在のお題一覧を取得
        odailist = self.repository.loadAll()

        # 2.該当ファイルをフィルタ
        newOdaiList = [o for o in odailist if o.file != filename]

        # 3.該当ファイルが存在するかチェック
        if len(newOdaiList) == len(odailist):
            return f"⚠️ {filename} は登録されていません"
        
        # 4.ファイル削除(登録)
        self.repository.saveAll(newOdaiList)

        return f"🗑️ {filename} をお題出力から除外しました。/odai_registerで再登録できます。"