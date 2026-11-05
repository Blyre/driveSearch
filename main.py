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


def _empty_metric_bucket() -> dict[str, int]:
    return {"total": 0, "new": 0, "used": 0, "runs": 0}


def _increment_metrics(metrics: dict[str, dict[str, int]], site: str, condition: str) -> None:
    bucket = metrics.setdefault(site, _empty_metric_bucket())
    bucket["total"] += 1
    if condition in ("new", "used"):
        bucket[condition] += 1


def scrape_and_alert() -> None:
    log.info("Starting scrape run...")
    st = state.load()
    seen_urls: set[str] = set(st["seen_urls"])
    new_deals: list[dict] = []
    daily_metrics = st["daily_metrics"]
    site_counts: dict[str, dict[str, int]] = daily_metrics["site_counts"]
    near_threshold_counts: dict[str, dict[str, int]] = daily_metrics["near_threshold_counts"]
    near_threshold_upper = config.PRICE_THRESHOLD_EUR * 1.10

    for scrape_fn, source_name in [
        (scrape_ebay, "eBay.de"),
        (scrape_servershop24, "servershop24.de"),
    ]:
        try:
            listings = scrape_fn()
        except Exception as exc:
            log.error(f"[{source_name}] scraper crashed: {exc}")
            continue

        site_counts.setdefault(source_name, _empty_metric_bucket())["runs"] += 1
        for listing in listings:
            _increment_metrics(site_counts, source_name, listing.condition)
            if config.PRICE_THRESHOLD_EUR <= listing.price < near_threshold_upper:
                _increment_metrics(near_threshold_counts, source_name, listing.condition)

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
    st["daily_metrics"] = daily_metrics
    state.save(st)
    log.info(f"Scrape run done. {len(new_deals)} new deal(s) alerted.")


def send_digest() -> None:
    log.info("Sending daily digest...")
    st = state.load()
    notifier.send_daily_digest(
        st.get("daily_deals", []),
        st.get("daily_metrics", {}),
        config.PRICE_THRESHOLD_EUR,
    )
    st["daily_deals"] = []  # reset accumulator after digest
    st["daily_metrics"] = {
        "site_counts": {},
        "near_threshold_counts": {},
    }
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
