"""
Minimal HTTP server for eBay's Marketplace Account Deletion notification endpoint.

eBay requires all production apps to register a publicly-accessible HTTPS endpoint
that can receive account-deletion events (GDPR compliance). The endpoint must:
  1. Respond to GET ?challenge_code=<value> with the SHA-256 challenge response.
  2. Acknowledge POST account-deletion payloads with HTTP 200.

Set these in .env:
  EBAY_VERIFICATION_TOKEN   — secret token you choose when registering the endpoint
  EBAY_NOTIFICATION_ENDPOINT_URL — the public HTTPS URL eBay will call (e.g. https://you.example.com/ebay/notifications)
  EBAY_NOTIFICATION_PORT    — local port to listen on (default: 8080)
"""

import hashlib
import json
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

import config

log = logging.getLogger(__name__)


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        params = parse_qs(urlparse(self.path).query)
        if "challenge_code" not in params:
            self._respond(200, b"OK")
            return

        challenge = params["challenge_code"][0]
        digest = hashlib.sha256(
            (challenge + config.EBAY_VERIFICATION_TOKEN + config.EBAY_NOTIFICATION_ENDPOINT_URL).encode()
        ).hexdigest()
        body = json.dumps({"challengeResponse": digest}).encode()
        self._respond(200, body, content_type="application/json")
        log.info("[eBay notif] challenge verification answered")

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)
        self._respond(200, b"")
        log.info("[eBay notif] account-deletion notification received and acknowledged")

    def _respond(self, code: int, body: bytes, content_type: str = "text/plain") -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if body:
            self.wfile.write(body)

    def log_message(self, fmt, *args):
        log.debug("[eBay notif] " + fmt % args)


def start() -> None:
    """Blocking call — run in a daemon thread."""
    server = HTTPServer(("0.0.0.0", config.EBAY_NOTIFICATION_PORT), _Handler)
    log.info(
        f"[eBay notif] listening on port {config.EBAY_NOTIFICATION_PORT} — "
        f"endpoint URL: {config.EBAY_NOTIFICATION_ENDPOINT_URL}"
    )
    server.serve_forever()
