import os

class GuildDataPathResolver:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    BASE_JSON_DIR = os.path.join(BASE_DIR, "Data")
    BASE_IMAGE_DIR = os.path.join(BASE_DIR, "templates")

    @staticmethod
    def get_odaijson_path(guild_id: int):
        json_dir = os.path.join(GuildDataPathResolver.BASE_JSON_DIR, str(guild_id))
        os.makedirs(json_dir, exist_ok=True)
        return os.path.join(json_dir, f"{guild_id}_odai.json")
    
    @staticmethod
    def get_schedulejson_path(guild_id: int):
        json_dir = os.path.join(GuildDataPathResolver.BASE_JSON_DIR, str(guild_id))
        os.makedirs(json_dir, exist_ok=True)
        return os.path.join(json_dir, f"{guild_id}_Schedule.json")

    @staticmethod
    def get_image_dir(guild_id: int):
        path = os.path.join(GuildDataPathResolver.BASE_IMAGE_DIR, str(guild_id))
        os.makedirs(path, exist_ok=True)
        return path
