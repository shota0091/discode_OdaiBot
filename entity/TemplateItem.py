class TemplateItem:
    def __init__(self, id, guild_id, filename, display_name, file_path, file_size, created_by, created_at):
        self.id = id
        self.guild_id = guild_id
        self.filename = filename
        self.display_name = display_name
        self.file_path = file_path
        self.file_size = file_size
        self.created_by = created_by
        self.created_at = created_at

    @staticmethod
    def from_row(row):
        # DictCursor 対応
        if isinstance(row, dict):
            return TemplateItem(
                row.get("id"),
                row.get("guild_id"),
                row.get("filename"),
                row.get("display_name"),
                row.get("file_path"),
                row.get("file_size"),
                row.get("created_by"),
                row.get("created_at"),
            )
        # 位置タプル対応
        return TemplateItem(*row)
