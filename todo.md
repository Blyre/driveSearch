# driveSearch — pending setup

## eBay Browse API — production compliance

The eBay Browse API requires two things before it works end-to-end:

### 1. Fix the truncated Cert ID (OAuth 401)

The current `EBAY_CLIENT_SECRET` in `.env` is too short (~36 chars) and gets rejected.

- Go to **https://developer.ebay.com/my/keys** → **Production** tab
- Re-copy the full **Cert ID** (≈50+ chars, starts with `PRD-`)
- Update `EBAY_CLIENT_SECRET` in `.env`
- Restart: `docker compose up -d` (no rebuild needed)

### 2. Register the notification endpoint (compliance gate)

eBay flags the app as non-compliant — and blocks API access — until a publicly
reachable HTTPS endpoint is registered for Marketplace Account Deletion events
(GDPR requirement). The receiver is already implemented in `ebay_notif.py` and
starts automatically once the two env vars below are set.

**What the endpoint does:**

- `GET /?challenge_code=<x>` → responds with a SHA-256 hash to prove ownership
- `POST /` → acknowledges account-deletion events with HTTP 200

**Public URL:** `https://ebay.cinderlabs.uk` via Cloudflare Tunnel
(hostname `ebay.cinderlabs.uk` → `drive-search-scraper:8082` already configured in
Cloudflare Zero Trust → Networks → Tunnels → homelab → Routes → Publish application)

**To finish setup:**

1. Add to `.env`:
   ```
   EBAY_VERIFICATION_TOKEN=<any long random string you choose>
   EBAY_NOTIFICATION_ENDPOINT_URL=https://ebay.cinderlabs.uk
   EBAY_NOTIFICATION_PORT=8082
   ```
2. Restart: `docker compose up -d`
3. In the eBay Developer Portal → your app → **Event Notification Delivery Method**:
   - URL: `https://ebay.cinderlabs.uk`
   - Verification token: same value as `EBAY_VERIFICATION_TOKEN`
   - Click **"Send Test Notification"** — eBay does a `GET ?challenge_code=xxx` to verify
4. Once verified the app turns compliant and the Browse API becomes accessible
