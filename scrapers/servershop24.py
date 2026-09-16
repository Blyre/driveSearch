import re
import time
import random
import logging

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError

import config
from .base import Listing

log = logging.getLogger(__name__)

_TARGET_MODELS = ("ST4000NM0033", "HUS726040ALA610", "HUS724040ALA640", "WD4000FYYZ")
_SEARCH_URLS = [
    f"https://www.servershop24.de/search/?q={model}&items_per_page=100"
    for model in _TARGET_MODELS
]

_PRODUCT_URL_RE = re.compile(r"/a-\d+/")


def _parse_price(text: str) -> float | None:
    match = re.search(r"([\d.]*\d+),(\d{2})\s*€", text)
    if not match:
        return None
    return float(match.group(1).replace(".", "") + "." + match.group(2))


def _clean_title(raw: str) -> str:
    # servershop24 sometimes duplicates the title in link text
    words = raw.split()
    half = len(words) // 2
    if half > 0 and words[:half] == words[half:]:
        return " ".join(words[:half])
    return raw


def _is_target_drive(title: str) -> bool:
    t = title.upper()
    return any(m in t for m in _TARGET_MODELS)


def _parse_rendered_html(html: str, seen_urls: set[str]) -> list[Listing]:
    listings: list[Listing] = []
    soup = BeautifulSoup(html, "lxml")

    items = (
        soup.select("ul.product-list li")
        or soup.select("div.product-list-item")
        or soup.select("li.product-list-item")
        or soup.select("article.product-item")
    )

    if items:
        for item in items:
            link_el = item.select_one("a[href]")
            if not link_el:
                continue
            url = link_el["href"]
            if not url.startswith("http"):
                url = "https://www.servershop24.de" + url
            if url in seen_urls or not _PRODUCT_URL_RE.search(url):
                continue

            title = _clean_title(item.get_text(" ", strip=True))
            price = _parse_price(item.get_text())
            if not title or price is None or not _is_target_drive(title):
                continue

            condition = "used" if "b-ware" in title.lower() else "new"
            seen_urls.add(url)
            listings.append(Listing(
                title=title, price=price, url=url,
                source="servershop24.de", condition=condition,
            ))
    else:
        # Fallback: find product links and walk DOM upward to find the price
        for link in soup.select("a[href]"):
            url = link["href"]
            if not url.startswith("http"):
                url = "https://www.servershop24.de" + url
            if url in seen_urls or not _PRODUCT_URL_RE.search(url):
                continue

            title = _clean_title(link.get_text(strip=True))
            if not title or not _is_target_drive(title):
                continue

            container, price = link.parent, None
            for _ in range(5):
                price = _parse_price(container.get_text())
                if price is not None:
                    break
                if container.parent is None:
                    break
                container = container.parent

            if price is None:
                continue

            condition = "used" if "b-ware" in title.lower() else "new"
            seen_urls.add(url)
            listings.append(Listing(
                title=title, price=price, url=url,
                source="servershop24.de", condition=condition,
            ))

    return listings


def scrape() -> list[Listing]:
    listings: list[Listing] = []
    seen_urls: set[str] = set()
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                executable_path=config.CHROMIUM_EXECUTABLE_PATH or None,
            )
            try:
                for search_url in _SEARCH_URLS:
                    page = browser.new_page()
                    try:
                        page.goto(search_url, timeout=30000, wait_until="networkidle")
                        try:
                            page.wait_for_selector(
                                "ul.product-list li, category-item", timeout=8000
                            )
                        except PWTimeoutError:
                            pass
                        listings.extend(_parse_rendered_html(page.content(), seen_urls))
                    finally:
                        page.close()
                    time.sleep(random.uniform(0.5, 1.5))
            finally:
                browser.close()
    except Exception as exc:
        log.error(f"[servershop24] scraper failed: {exc}")

    log.info(f"[servershop24] scraped {len(listings)} matching listing(s)")
    return listings
