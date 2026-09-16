import re
import time
import random
import logging

import requests
from bs4 import BeautifulSoup

from .base import Listing

log = logging.getLogger(__name__)

_BASE_URL = "https://www.servershop24.de"
_SEARCH_URL = (
    "https://www.servershop24.de/search/"
    "?q=4TB+3.5+SATA+Festplatte"
    "&items_per_page=100"
)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "de-DE,de;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# Product URLs on servershop24 always end with /a-<digits>/
_PRODUCT_URL_RE = re.compile(r"/a-\d+/")


def _parse_price(text: str) -> float | None:
    match = re.search(r"([\d.]*\d+),(\d{2})\s*€", text)
    if not match:
        return None
    return float(match.group(1).replace(".", "") + "." + match.group(2))


def _clean_title(raw: str) -> str:
    """servershop24 link text duplicates the title; keep only the first half."""
    words = raw.split()
    half = len(words) // 2
    if half > 0 and words[:half] == words[half:]:
        return " ".join(words[:half])
    return raw


def _is_sata_4tb(title: str) -> bool:
    # Search query already includes "3.5"; skip form-factor check to avoid missing LFF listings
    t = title.lower()
    return "sata" in t and ("4tb" in t.replace(" ", "") or "4 tb" in t)


def scrape() -> list[Listing]:
    listings: list[Listing] = []
    try:
        resp = requests.get(_SEARCH_URL, headers=_HEADERS, timeout=20)
        resp.raise_for_status()
    except requests.RequestException as exc:
        log.error(f"[servershop24] request failed: {exc}")
        return listings

    soup = BeautifulSoup(resp.text, "lxml")
    seen_urls: set[str] = set()
    items = (
        soup.select("div.product-list-item")
        or soup.select("li.product-list-item")
        or soup.select("article.product-item")
        or soup.select(".cmp-product-thumb")
    )

    if items:
        for item in items:
            link_el = item.select_one("a[href]")
            price_el = (
                item.select_one(".price")
                or item.select_one("[class*='price']")
                or item.select_one(".content-price")
            )
            if not link_el:
                continue
            url = link_el["href"]
            if not url.startswith("http"):
                url = _BASE_URL + url
            if url in seen_urls or not _PRODUCT_URL_RE.search(url):
                continue

            title = _clean_title(link_el.get_text(strip=True))
            price_text = price_el.get_text() if price_el else item.get_text()
            price = _parse_price(price_text)

            if not title or price is None or not _is_sata_4tb(title):
                continue

            condition = "used" if "b-ware" in title.lower() else "new"
            seen_urls.add(url)
            listings.append(Listing(
                title=title, price=price, url=url,
                source="servershop24.de", condition=condition,
            ))
    else:
        # Fallback: parse all product anchor tags and extract price from link text
        for link in soup.select("a[href]"):
            url = link["href"]
            if not url.startswith("http"):
                url = _BASE_URL + url
            if url in seen_urls or not _PRODUCT_URL_RE.search(url):
                continue

            link_text = link.get_text(" ", strip=True)
            title = _clean_title(link_text)
            price = _parse_price(link_text)

            if not title or price is None or not _is_sata_4tb(title):
                continue

            condition = "used" if "b-ware" in title.lower() else "new"
            seen_urls.add(url)
            listings.append(Listing(
                title=title, price=price, url=url,
                source="servershop24.de", condition=condition,
            ))

    log.info(f"[servershop24] scraped {len(listings)} matching listings")
    time.sleep(random.uniform(1.0, 2.5))
    return listings
