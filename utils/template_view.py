# utils/template_view.py
import os
import discord
from discord.ui import View, button

class TemplateGalleryView(View):
    """テンプレをグリッド（複数件/ページ）で表示。各アイテムは個別のEmbedに画像を載せる。"""
    def __init__(self, templates, per_page: int = 4, timeout: int = 180):
        super().__init__(timeout=timeout)
        # Discord 制限: 1メッセージあたり embeds<=10, files<=10
        self.per_page = max(1, min(per_page, 10))
        self.templates = templates
        self.page = 0
        self._sync_buttons()

    # -- ページ計算
    def _pages(self) -> int:
        total = len(self.templates)
        return max(1, (total + self.per_page - 1) // self.per_page)

    def _slice(self):
        s = self.page * self.per_page
        e = s + self.per_page
        return self.templates[s:e], s

    # -- 送信ペイロード（複数Embed＋複数File）
    def build_payload(self):
      import os
      items, base_idx = self._slice()
      embeds, files = [], []

        # ページ情報を最初に出す
      header = discord.Embed(title=f"テンプレート一覧 {self.page+1}/{self._pages()}")
      embeds.append(header)

      # このページに含まれるテンプレートだけループ
      for idx_on_page, t in enumerate(items, start=1):
        i = base_idx + idx_on_page
        name = t.display_name
        rel  = t.file_path
        abs_path = os.path.abspath(rel) if rel else None

        em = discord.Embed(title=f"{i}. {name}")

        if abs_path and os.path.exists(abs_path):
            attach_name = f"tpl_{self.page}_{idx_on_page}__{os.path.basename(abs_path)}"
            files.append(discord.File(abs_path, filename=attach_name))
            em.set_thumbnail(url=f"attachment://{attach_name}")
        else:
            em.set_footer(text="⚠ 画像ファイルが見つかりません")

        embeds.append(em)

      return embeds, files
    
    def _sync_buttons(self):
        if hasattr(self, "prev_btn"):
            self.prev_btn.disabled = (self.page <= 0)
        if hasattr(self, "next_btn"):
            self.next_btn.disabled = ((self.page + 1) >= self._pages())

    async def _edit(self, interaction: discord.Interaction):
        self._sync_buttons()
        embeds, files = self.build_payload()
        await interaction.response.edit_message(embeds=embeds, attachments=files, view=self)

    @button(label="◀ 前へ", style=discord.ButtonStyle.secondary, custom_id="tplg_prev")
    async def prev_btn(self, interaction: discord.Interaction, _):
        if self.page > 0:
            self.page -= 1
        await self._edit(interaction)

    @button(label="次へ ▶", style=discord.ButtonStyle.secondary, custom_id="tplg_next")
    async def next_btn(self, interaction: discord.Interaction, _):
        if (self.page + 1) < self._pages():
            self.page += 1
        await self._edit(interaction)

def build_embed_and_files(self):
    import os
    items = self._page_slice()
    idx_start = self.page * self.per_page
    total_pages = self._pages()

    embed = discord.Embed(title=f"テンプレート一覧 {self.page+1}/{total_pages}")
    files = []

    for idx_on_page, t in enumerate(items, start=1):
        i = idx_start + idx_on_page
        name = t.display_name
        rel  = t.file_path
        abs_path = os.path.abspath(rel) if rel else None

        embed.add_field(name=f"{i}. {name}", value="\u200b", inline=False)

        if abs_path and os.path.exists(abs_path):
            attach_name = f"tpl_{self.page}_{idx_on_page}__{os.path.basename(abs_path)}"
            files.append(discord.File(abs_path, filename=attach_name))
            embed.set_thumbnail(url=f"attachment://{attach_name}")  # ← サムネ表示
        else:
            embed.set_footer(text="⚠ 画像ファイルが見つかりません")

    return embed, files