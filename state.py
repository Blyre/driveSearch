import copy
import json
import os
from pathlib import Path

_STATE_FILE = Path(os.getenv("STATE_FILE_PATH", "seen.json"))
_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)


def _empty_metric_bucket() -> dict[str, int]:
    return {"total": 0, "new": 0, "used": 0, "runs": 0}


def _normalize_metric_map(metric_map: dict) -> dict[str, dict[str, int]]:
    normalized: dict[str, dict[str, int]] = {}
    for site, value in metric_map.items():
        if isinstance(value, dict):
            normalized[site] = {
                "total": int(value.get("total", 0)),
                "new": int(value.get("new", 0)),
                "used": int(value.get("used", 0)),
                "runs": int(value.get("runs", 0)),
            }
            continue

        normalized[site] = _empty_metric_bucket()
        normalized[site]["total"] = int(value)
    return normalized


_DEFAULT_STATE = {
    "seen_urls": [],
    "daily_deals": [],
    "daily_metrics": {
        "site_counts": {},
        "near_threshold_counts": {},
    },
    "last_digest_at": None,
}


def load() -> dict:
    if _STATE_FILE.exists():
        if _STATE_FILE.is_dir():
            raise IsADirectoryError(f"State path is a directory: {_STATE_FILE}")
        st = json.loads(_STATE_FILE.read_text(encoding="utf-8"))
    else:
        st = copy.deepcopy(_DEFAULT_STATE)

    for key, value in _DEFAULT_STATE.items():
        st.setdefault(key, copy.deepcopy(value))
    st["daily_metrics"].setdefault("site_counts", {})
    st["daily_metrics"].setdefault("near_threshold_counts", {})
    st["daily_metrics"]["site_counts"] = _normalize_metric_map(
        st["daily_metrics"]["site_counts"]
    )
    st["daily_metrics"]["near_threshold_counts"] = _normalize_metric_map(
        st["daily_metrics"]["near_threshold_counts"]
    )
    return st


def save(st: dict) -> None:
    if _STATE_FILE.exists() and _STATE_FILE.is_dir():
        raise IsADirectoryError(f"State path is a directory: {_STATE_FILE}")
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(
        json.dumps(st, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
