import os

class GuildDataPathResolver:

    BASE_JSON_DIR = "Data"
    BASE_IMAGE_DIR = "templates"

    @staticmethod
    def get_odaijson_path(guild_id: int):
        json_dir = GuildDataPathResolver.BASE_JSON_DIR
        os.makedirs(json_dir, exist_ok=True)
        return f"{json_dir}/{guild_id}_odai.json"
    
    @staticmethod
    def get_schedulejson_path(guild_id: int):
        json_dir = GuildDataPathResolver.BASE_JSON_DIR
        os.makedirs(json_dir, exist_ok=True)
        return f"{json_dir}/{guild_id}_Schedule.json"

    @staticmethod
    def get_image_dir(guild_id: int):
        path = f"{GuildDataPathResolver.BASE_IMAGE_DIR}/{guild_id}"
        os.makedirs(path, exist_ok=True)
        return path
