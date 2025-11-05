import os
from dotenv import load_dotenv
from Bot.OdaiBot import OdaiBot

# .env読み込み
load_dotenv()

def main():
    token = os.getenv("DISCORD_BOT_TOKEN")
    json_path = os.getenv("ODAI_JSON_PATH")
    image_dir = os.getenv("ODAI_IMAGE_DIR")

    if not token:
        raise Exception("❌ DISCORD_BOT_TOKEN が .env に設定されていません")
    
    print("🚀 OdaiBot 起動中...")
    bot = OdaiBot(
        token=token,
        jsonPath=json_path,
        imageDir=image_dir
    )
    bot.run_bot()

if __name__ == "__main__":
    main()
