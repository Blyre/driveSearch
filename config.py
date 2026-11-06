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
# eBay Marketplace Account Deletion notification endpoint (required for production compliance)
# EBAY_VERIFICATION_TOKEN: a secret string you choose when registering the endpoint in the portal
# EBAY_NOTIFICATION_ENDPOINT_URL: the public HTTPS URL eBay will POST events to
EBAY_VERIFICATION_TOKEN: str = os.getenv("EBAY_VERIFICATION_TOKEN", "")
EBAY_NOTIFICATION_ENDPOINT_URL: str = os.getenv("EBAY_NOTIFICATION_ENDPOINT_URL", "")
EBAY_NOTIFICATION_PORT: int = int(os.getenv("EBAY_NOTIFICATION_PORT", "8082"))
