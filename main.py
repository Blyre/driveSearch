import logging
import time
from dataclasses import asdict

import schedule

import config
import notifier
import state
from scrapers.ebay import scrape as scrape_ebay
from scrapers.servershop24 import scrape as scrape_servershop24

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
log = logging.getLogger(__name__)


def scrape_and_alert() -> None:
    log.info("Starting scrape run...")
    st = state.load()
    seen_urls: set[str] = set(st["seen_urls"])
    new_deals: list[dict] = []

    for scrape_fn, name in [
        (scrape_ebay, "eBay"),
        (scrape_servershop24, "servershop24"),
    ]:
        try:
            listings = scrape_fn()
        except Exception as exc:
            log.error(f"[{name}] scraper crashed: {exc}")
            continue

        for listing in listings:
            if listing.price >= config.PRICE_THRESHOLD_EUR:
                continue
            if listing.url in seen_urls:
                continue
            notifier.send_deal_alert(listing, config.PRICE_THRESHOLD_EUR)
            seen_urls.add(listing.url)
            new_deals.append(asdict(listing))

    st["seen_urls"] = list(seen_urls)
    st["daily_deals"] = st.get("daily_deals", []) + new_deals
    state.save(st)
    log.info(f"Scrape run done. {len(new_deals)} new deal(s) alerted.")


def send_digest() -> None:
    log.info("Sending daily digest...")
    st = state.load()
    notifier.send_daily_digest(st.get("daily_deals", []))
    st["daily_deals"] = []  # reset accumulator after digest
    state.save(st)
    log.info("Daily digest sent.")


def main() -> None:
    log.info(
        f"Drive deal scraper started — "
        f"scraping every {config.SCRAPE_INTERVAL_HOURS}h, "
        f"digest every {config.DIGEST_INTERVAL_HOURS}h, "
        f"threshold €{config.PRICE_THRESHOLD_EUR}"
    )

    # Run immediately on startup so we don't wait for the first interval
    scrape_and_alert()

    schedule.every(config.SCRAPE_INTERVAL_HOURS).hours.do(scrape_and_alert)
    schedule.every(config.DIGEST_INTERVAL_HOURS).hours.do(send_digest)

    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    main()
