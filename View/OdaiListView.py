from discord import Embed, File
import os

"""
お題Bot実行クラス
Args:
  odai_list (list[str]): 一覧表示するお題のList(ファイル名)
Returns:
  Embed: お題を一覧表示するview
  file: 表示用のサムネイル
"""
class OdaiListView:
  @staticmethod
  def build(odai, index: int, total: int, image_dir: str):
        embed = Embed(
            title=f"📂 登録済みお題一覧（{index+1}/{total}件）",
            description=f"・`{odai.file}`",
            color=0x3498db
        )
        embed.set_footer(text="OdaiBot")

        img_path = os.path.join(image_dir, odai.file)
        file = None

        if os.path.exists(img_path):
            file = File(img_path, filename="thumb.png")
            embed.set_thumbnail(url="attachment://thumb.png")

        return embed, file