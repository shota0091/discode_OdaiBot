from dataclasses import dataclass
from typing import Optional
from datetime import datetime
from typing import Any, Dict

@dataclass
class OdaiItem:
    id: Optional[int]
    guild_id: int
    channel_id: Optional[int]
    content: str
    image_path: Optional[str]
    is_sent: bool
    created_by: int
    created_at: Optional[datetime] = None


@dataclass
class TemplateItem:
    id: int
    guild_id: int
    filename: str
    display_name: str
    file_path: str
    file_size: int
    created_by: int
    created_at: str  # datetime型でも可（用途に応じて）

    @staticmethod
    def from_row(row: Dict[str, Any]) -> 'TemplateItem':
        return TemplateItem(
            id=row["id"],
            guild_id=row["guild_id"],
            filename=row["filename"],
            display_name=row["display_name"],
            file_path=row["file_path"],
            file_size=row["file_size"],
            created_by=row["created_by"],
            created_at=str(row["created_at"])  # 必要に応じて str() を除外
        )
