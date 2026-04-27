from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class OdaiEntity:
    file: str
    used: bool = False
    added_at: str = field(default_factory=lambda: datetime.now().isoformat())