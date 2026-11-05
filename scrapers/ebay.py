import base64
import logging
import time

import requests

import config
from .base import Listing

log = logging.getLogger(__name__)

_TARGET_MODELS = ("ST4000NM0033", "HUS726040ALA610", "HUS724040ALA640", "WD4000FYYZ")

_OAUTH_URL = "https://api.ebay.com/identity/v1/oauth2/token"
_BROWSE_URL = "https://api.ebay.com/buy/browse/v1/item_summary/search"

_cached_token: str | None = None
_token_expiry: float = 0.0


def _get_access_token() -> str:
    global _cached_token, _token_expiry
    if _cached_token and time.time() < _token_expiry - 60:
        return _cached_token

    creds = base64.b64encode(
        f"{config.EBAY_CLIENT_ID}:{config.EBAY_CLIENT_SECRET}".encode()
    ).decode()
    resp = requests.post(
        _OAUTH_URL,
        headers={
            "Authorization": f"Basic {creds}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "client_credentials",
            "scope": "https://api.ebay.com/oauth/api_scope",
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    _cached_token = data["access_token"]
    _token_expiry = time.time() + int(data.get("expires_in", 7200))
    return _cached_token


def _is_target_drive(title: str) -> bool:
    t = title.upper()
    return any(m in t for m in _TARGET_MODELS)


def scrape() -> list[Listing]:
    if not (config.EBAY_CLIENT_ID and config.EBAY_CLIENT_SECRET):
        log.warning(
            "[eBay] EBAY_CLIENT_ID / EBAY_CLIENT_SECRET not set — skipping. "
            "Register a free app at https://developer.ebay.com to enable eBay scraping."
        )
        return []

    listings: list[Listing] = []

    try:
        token = _get_access_token()
    except Exception as exc:
        log.error(f"[eBay] OAuth token request failed: {exc}")
        return listings

    headers = {
        "Authorization": f"Bearer {token}",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_DE",
    }
    params = {
        "q": "|".join(_TARGET_MODELS),
        "filter": "buyingOptions:{FIXED_PRICE}",
        "sort": "price",
        "limit": 200,
        "category_ids": "131553",  # Internal Hard Disk Drives on eBay.de
    }

    try:
        resp = requests.get(_BROWSE_URL, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        log.error(f"[eBay] Browse API request failed: {exc}")
        return listings

    for item in data.get("itemSummaries", []):
        title = item.get("title", "")
        if not _is_target_drive(title):
            continue

        price_info = item.get("price", {})
        try:
            price = float(price_info.get("value", 0))
        except (ValueError, TypeError):
            continue

        url = item.get("itemWebUrl", "")
        condition_str = item.get("condition", "").lower()
        condition = "new" if condition_str == "new" else "used"

        listings.append(Listing(
            title=title, price=price, url=url,
            source="eBay.de", condition=condition,
        ))

    log.info(f"[eBay] API returned {len(listings)} matching listing(s)")
    return listings
