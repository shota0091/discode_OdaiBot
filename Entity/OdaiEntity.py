from dataclasses import dataclass,field
from datetime import datetime
#odaiBotのEntityクラス
class OdaiEntity:
  field: str
  used: bool = False
  added_at: str = field(default_factory=lambda: datetime.now().isoformat())