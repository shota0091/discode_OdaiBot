import discord
from discord.ext import commands
from discord import app_commands
from Factory.OdaiFactory import OdaiFactory
from View.OdaiListView import OdaiListView
from View.OdaiListViewUI import OdaiListViewUI

class OdaiBot(commands.Bot):
    def __init__(self, token: str, jsonPath: str, imageDir: str):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

        factory = OdaiFactory(jsonPath, imageDir)
        self.notifyService = factory.getNotifyService()
        self.registerService = factory.getRegisterService()
        self.repository = factory.getRepository()

        self.token = token
        self.imageDir = imageDir

    async def setup_hook(self):
        guild = discord.Object(id=1396823594411098223)

        cmds = [
            self.slash_odai,
            self.slash_odai_add,
            self.slash_odai_register,
            self.slash_odai_list,
            self.slash_ping  # ← testping に変えたシグネチャのやつ
        ]

        for cmd in cmds:
            self.tree.add_command(cmd, guild=guild)

        await self.tree.sync(guild=guild)
        print("✅ Slash commands synced")


    @app_commands.command(name="testping", description="Bot応答テスト")
    async def slash_ping(self, interaction: discord.Interaction):
        print("⚡ ping received")
        await interaction.response.send_message("pong!")
    # ---- Slash commands -----


    @app_commands.command(name="odai", description="今日のお題を送信")
    async def slash_odai(self, interaction: discord.Interaction):
        image_path = self.notifyService.sendNotifyOdai()
        await interaction.response.send_message(file=discord.File(image_path))

    @app_commands.command(name="odai_add", description="画像を追加して登録")
    async def slash_odai_add(self, interaction: discord.Interaction, image: discord.Attachment):
        save_path = f"{self.imageDir}/{image.filename}"
        await image.save(save_path)
        result = self.registerService.add_odai(save_path)
        await interaction.response.send_message(f"✅ {result}")

    @app_commands.command(name="odai_register", description="既存画像を登録")
    async def slash_odai_register(self, interaction: discord.Interaction, filename: str):
        result = self.registerService.add_odai(filename)
        await interaction.response.send_message(f"✅ {result}")

    @app_commands.command(name="odai_list", description="登録済みのお題を表示")
    async def slash_odai_list(self, interaction: discord.Interaction):
        odai_list = self.repository.loadAll()
        if not odai_list:
            await interaction.response.send_message("⚠️ お題がありません")
            return

        first = odai_list[0]
        embed, file = OdaiListView.build(first, 0, len(odai_list), self.imageDir)
        view = OdaiListViewUI(self, odai_list, 0, self.imageDir)

        await interaction.response.send_message(embed=embed, file=file, view=view)

    def run_bot(self):
        self.run(self.token)
