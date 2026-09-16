import re
import time
import random
import logging

import requests
from bs4 import BeautifulSoup

from .base import Listing

log = logging.getLogger(__name__)

_TARGET_MODELS = ("ST4000NM0033", "HUS726040ALA610", "HUS724040ALA640", "WD4000FYYZ")

_BASE_URL = "https://www.ebay.de/sch/i.html"
# Category 131553 = Internal Hard Disk Drives on ebay.de
# _sop=15 = lowest price + postage first, LH_BIN=1 = Buy It Now only
_SEARCH_PARAMS = {
    "_nkw": "(ST4000NM0033,HUS726040ALA610,HUS724040ALA640,WD4000FYYZ)",
    "_sop": "15",
    "LH_BIN": "1",
    "_sacat": "131553",
    "_ipg": "60",
}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,"
        "application/signed-exchange;v=b3;q=0.7"
    ),
    "Accept-Language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Cache-Control": "max-age=0",
    "Sec-Ch-Ua": '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
    "Sec-Ch-Ua-Mobile": "?0",
    "Sec-Ch-Ua-Platform": '"Linux"',
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


def _parse_price(text: str) -> float | None:
    """Extract the lowest price; handles ranges like '45,99 EUR bis 99,00 EUR'."""
    matches = re.findall(r"[\d.]*\d+,\d{2}", text)
    if not matches:
        return None
    return min(float(m.replace(".", "").replace(",", ".")) for m in matches)


def _is_target_drive(title: str) -> bool:
    t = title.upper()
    return any(m in t for m in _TARGET_MODELS)


def scrape() -> list[Listing]:
    listings: list[Listing] = []
    session = requests.Session()
    try:
        # Warm up the session to acquire cookies before the search request
        session.get("https://www.ebay.de/", headers=_HEADERS, timeout=15)
        time.sleep(random.uniform(1.0, 2.0))
        resp = session.get(_BASE_URL, params=_SEARCH_PARAMS, headers=_HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as exc:
        log.error(f"[eBay] request failed: {exc}")
        return listings

    soup = BeautifulSoup(resp.text, "lxml")

    for item in soup.select("li.s-item"):
        title_el = item.select_one(".s-item__title")
        price_el = item.select_one(".s-item__price")
        link_el = item.select_one("a.s-item__link")

        if not (title_el and price_el and link_el):
            continue

        title = title_el.get_text(strip=True)
        if title.lower() in ("shop on ebay", ""):
            continue

        price = _parse_price(price_el.get_text())
        if price is None:
            continue

        # Strip eBay tracking parameters from URL
        url = link_el["href"].split("?")[0]

        cond_el = item.select_one(".SECONDARY_INFO")
        condition_text = cond_el.get_text(strip=True).lower() if cond_el else ""
        condition = "new" if "neu" in condition_text else "used"

        if not _is_target_drive(title):
            continue

        listings.append(Listing(
            title=title,
            price=price,
            url=url,
            source="eBay.de",
            condition=condition,
        ))

    log.info(f"[eBay] scraped {len(listings)} matching listings")
    time.sleep(random.uniform(1.5, 3.5))
    return listings
