from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Listing:
    title: str
    price: float
    url: str
    source: str       # "eBay.de" | "servershop24.de"
    condition: str    # "new" | "used"
    found_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
