from dataclasses import dataclass, field
from datetime import datetime

@dataclass
class OdaiEntity:
    file: str
    added_at: str = field(default_factory=lambda: datetime.now().isoformat())