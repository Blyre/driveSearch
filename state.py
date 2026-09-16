import json
from pathlib import Path

_STATE_FILE = Path("seen.json")


def load() -> dict:
    if _STATE_FILE.exists():
        return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
    return {"seen_urls": [], "daily_deals": [], "last_digest_at": None}


def save(st: dict) -> None:
    _STATE_FILE.write_text(
        json.dumps(st, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
