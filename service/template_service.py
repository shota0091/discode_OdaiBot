from repository.template_repository import TemplateRepository
from entity.TemplateItem import TemplateItem

class TemplateLimitExceeded(Exception): pass
class TemplateAlreadyExists(Exception): pass
class TemplateNotFound(Exception): pass

class TemplateService:
    MAX_TEMPLATES = 5

    def __init__(self, repo: TemplateRepository):
        self.repo = repo

    def register(self, guild_id, filename, display_name, file_path, file_size, created_by):
        if self.repo.count_by_guild(guild_id) >= self.MAX_TEMPLATES:
            raise TemplateLimitExceeded("このサーバーではテンプレートを5件までしか登録できません。")
        if self.repo.get_by_name(guild_id, display_name):
            raise TemplateAlreadyExists("同名のテンプレートが既に存在します。")
        return self.repo.insert(guild_id, filename, display_name, file_path, file_size, created_by)

    def delete(self, guild_id, display_name):
        affected = self.repo.delete_by_name(guild_id, display_name)
        if affected == 0:
            raise TemplateNotFound("指定のテンプレートが見つかりません。")
        return affected

    def list(self, guild_id):
        return self.repo.list_by_guild(guild_id)
