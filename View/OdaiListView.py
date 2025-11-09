from discord import Embed, File
import os

class OdaiListView:
    @staticmethod
    def build(odai, index: int, total: int, image_dir: str):
        filename = odai["file"]  # ✅ dict対応

        embed = Embed(
            title=f"📂 登録済みお題一覧（{index+1}/{total}件）",
            description=f"・`{filename}`",
            color=0x3498db
        )
        embed.set_footer(text="OdaiBot")

        file_path = os.path.join(image_dir, filename)
        file = File(file_path, filename=filename)

        embed.set_image(url=f"attachment://{filename}")

        return embed, file
