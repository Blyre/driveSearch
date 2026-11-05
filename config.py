import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_WEBHOOK_URL: str = os.environ["DISCORD_WEBHOOK_URL"]
PRICE_THRESHOLD_EUR: float = float(os.getenv("PRICE_THRESHOLD_EUR", "70.0"))
SCRAPE_INTERVAL_HOURS: int = int(os.getenv("SCRAPE_INTERVAL_HOURS", "6"))
DIGEST_INTERVAL_HOURS: int = int(os.getenv("DIGEST_INTERVAL_HOURS", "24"))
# Set to system chromium path to skip the playwright chromium download
CHROMIUM_EXECUTABLE_PATH: str | None = os.getenv("CHROMIUM_EXECUTABLE_PATH")
# eBay Browse API credentials — register a free app at https://developer.ebay.com
EBAY_CLIENT_ID: str | None = os.getenv("EBAY_CLIENT_ID")
EBAY_CLIENT_SECRET: str | None = os.getenv("EBAY_CLIENT_SECRET")
