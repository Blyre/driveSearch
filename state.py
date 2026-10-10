import json
import os
from pathlib import Path

_STATE_FILE = Path(os.getenv("STATE_FILE_PATH", "seen.json"))
_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)


def load() -> dict:
    if _STATE_FILE.exists():
        if _STATE_FILE.is_dir():
            raise IsADirectoryError(f"State path is a directory: {_STATE_FILE}")
        return json.loads(_STATE_FILE.read_text(encoding="utf-8"))
    return {"seen_urls": [], "daily_deals": [], "last_digest_at": None}


def save(st: dict) -> None:
    if _STATE_FILE.exists() and _STATE_FILE.is_dir():
        raise IsADirectoryError(f"State path is a directory: {_STATE_FILE}")
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(
        json.dumps(st, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
