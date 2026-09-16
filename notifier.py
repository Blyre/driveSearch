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


def send_daily_digest(deals: list[dict]) -> None:
    if not deals:
        embed = {
            "title": "Daily Digest — No deals found",
            "description": 'No deals below threshold were found in the last 24h for the target models.',
            "color": _COLOR_DIGEST,
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
        "footer": {"text": 'Top 10 cheapest: ST4000NM0033 / HUS726040ALA610 / HUS724040ALA640 / WD4000FYYZ'},
    }
    _post({"embeds": [embed]})
