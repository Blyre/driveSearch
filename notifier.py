import logging

import requests

import config
from scrapers.base import Listing

log = logging.getLogger(__name__)

_COLOR_DEAL = 0x57F287    # green
_COLOR_DIGEST = 0x5865F2  # Discord blurple


def _post(payload: dict) -> None:
    try:
        resp = requests.post(
            config.DISCORD_WEBHOOK_URL,
            json=payload,
            timeout=10,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        log.error(f"Discord webhook failed: {exc}")


def send_deal_alert(listing: Listing, threshold: float) -> None:
    embed = {
        "title": f"Deal found — {listing.source}",
        "description": f"**[{listing.title}]({listing.url})**",
        "color": _COLOR_DEAL,
        "fields": [
            {"name": "Price", "value": f"**€{listing.price:.2f}**", "inline": True},
            {"name": "Condition", "value": listing.condition.capitalize(), "inline": True},
            {"name": "Source", "value": listing.source, "inline": True},
        ],
        "footer": {"text": f'Threshold: €{threshold:.2f} | ST4000NM0033 / HUS726040ALA610 / HUS724040ALA640 / WD4000FYYZ'},
    }
    _post({"embeds": [embed]})


def _build_metrics_value(metrics: dict, threshold: float) -> str:
    site_counts = metrics.get("site_counts", {})
    near_threshold_counts = metrics.get("near_threshold_counts", {})
    sites = sorted(set(site_counts.keys()) | set(near_threshold_counts.keys()))
    if not sites:
        return "No scraper metrics recorded in the last 24h."

    def as_bucket(value: dict | int | None) -> dict[str, int]:
        if isinstance(value, dict):
            return {
                "total": int(value.get("total", 0)),
                "new": int(value.get("new", 0)),
                "used": int(value.get("used", 0)),
                "runs": int(value.get("runs", 0)),
            }
        return {"total": int(value or 0), "new": 0, "used": 0, "runs": 0}

    lines: list[str] = []
    for site in sites:
        found = as_bucket(site_counts.get(site))
        near_threshold = as_bucket(near_threshold_counts.get(site))
        lines.append(
            f"**{site}**: "
            f"{found['runs']} run(s) — "
            f"{found['total']} found (new {found['new']}, used {found['used']}); "
            f"{near_threshold['total']} within 10% above threshold "
            f"(new {near_threshold['new']}, used {near_threshold['used']})"
        )

    lines.append(f"\nThreshold: €{threshold:.2f}")
    return "\n".join(lines)


def send_daily_digest(deals: list[dict], metrics: dict, threshold: float) -> None:
    metrics_value = _build_metrics_value(metrics, threshold)
    if not deals:
        embed = {
            "title": "Daily Digest — No deals found",
            "description": 'No deals below threshold were found in the last 24h for the target models.',
            "color": _COLOR_DIGEST,
            "fields": [
                {"name": "Daily metrics", "value": metrics_value, "inline": False},
            ],
        }
        _post({"embeds": [embed]})
        return

    # Top 10 cheapest
    top = sorted(deals, key=lambda d: d["price"])[:10]
    lines = [
        f"{i}. **€{d['price']:.2f}** — [{d['title'][:70]}]({d['url']}) "
        f"*({d['source']}, {d['condition']})*"
        for i, d in enumerate(top, 1)
    ]
    embed = {
        "title": f"Daily Digest — {len(deals)} deal(s) in the last 24h",
        "description": "\n".join(lines),
        "color": _COLOR_DIGEST,
        "fields": [
            {"name": "Daily metrics", "value": metrics_value, "inline": False},
        ],
        "footer": {"text": 'Top 10 cheapest: ST4000NM0033 / HUS726040ALA610 / HUS724040ALA640 / WD4000FYYZ'},
    }
    _post({"embeds": [embed]})
