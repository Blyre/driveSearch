import re
import time
import random
import logging

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError
from playwright_stealth import Stealth

import config
from .base import Listing

log = logging.getLogger(__name__)

_TARGET_MODELS = ("ST4000NM0033", "HUS726040ALA610", "HUS724040ALA640", "WD4000FYYZ")

# Category 131553 = Internal Hard Disk Drives on ebay.de
# _sop=15 = lowest price + postage first, LH_BIN=1 = Buy It Now only
_SEARCH_URL = (
    "https://www.ebay.de/sch/i.html"
    "?_nkw=%28ST4000NM0033%2CHUS726040ALA610%2CHUS724040ALA640%2CWD4000FYYZ%29"
    "&_sop=15&LH_BIN=1&_sacat=131553&_ipg=60"
)


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
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled"],
                executable_path=config.CHROMIUM_EXECUTABLE_PATH or None,
            )
            try:
                context = browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
                    ),
                    locale="de-DE",
                )
                page = context.new_page()
                Stealth().apply_stealth_sync(page)
                page.goto(_SEARCH_URL, timeout=30000, wait_until="domcontentloaded")
                try:
                    page.wait_for_selector("li.s-item", timeout=15000)
                except PWTimeoutError:
                    log.warning("[eBay] timed out waiting for listing items")
                html = page.content()
            finally:
                browser.close()
    except Exception as exc:
        log.error(f"[eBay] scraper failed: {exc}")
        return listings

    soup = BeautifulSoup(html, "lxml")

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
            title=title, price=price, url=url,
            source="eBay.de", condition=condition,
        ))

    log.info(f"[eBay] scraped {len(listings)} matching listing(s)")
    time.sleep(random.uniform(1.0, 2.0))
    return listings
