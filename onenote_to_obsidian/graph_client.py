"""Microsoft Graph API HTTP client with retry logic and pagination."""

import logging
import time

import requests

from .auth import AuthManager

logger = logging.getLogger(__name__)

BASE_URL = "https://graph.microsoft.com/v1.0"

MAX_RETRIES = 3
BACKOFF_FACTOR = 2  # seconds: 2, 4, 8


class GraphAPIError(Exception):
    """Raised when a Graph API request fails after retries."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"Graph API error {status_code}: {message}")


class GraphClient:
    """HTTP client for Microsoft Graph API with automatic retry and pagination."""

    def __init__(self, auth: AuthManager):
        self._auth = auth
        self._session = requests.Session()
        self._session.headers["Accept"] = "application/json"

    def _get_headers(self, force_refresh: bool = False) -> dict:
        token = self._auth.get_token(force_refresh=force_refresh)
        return {"Authorization": f"Bearer {token}"}

    def _request_with_retry(
        self, method: str, url: str, *, accept: str | None = None, **kwargs
    ) -> requests.Response:
        """Execute an HTTP request with retry on 429, 5xx, and 401."""
        if not url.startswith("http"):
            url = f"{BASE_URL}{url}"

        headers = self._get_headers()
        if accept:
            headers["Accept"] = accept

        last_error = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                resp = self._session.request(method, url, headers=headers, timeout=60, **kwargs)
            except requests.RequestException as e:
                last_error = e
                if attempt < MAX_RETRIES:
                    wait = BACKOFF_FACTOR ** (attempt + 1)
                    logger.warning("Request failed (%s), retrying in %ds...", e, wait)
                    time.sleep(wait)
                    continue
                raise GraphAPIError(0, str(e)) from e

            if resp.status_code == 200:
                return resp

            if resp.status_code == 401 and attempt == 0:
                # Token might be expired; force refresh from identity provider
                logger.info("Got 401, forcing token refresh...")
                headers = self._get_headers(force_refresh=True)
                continue

            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 10))
                logger.warning("Rate limited (429), waiting %ds...", retry_after)
                time.sleep(retry_after)
                continue

            if resp.status_code >= 500:
                wait = BACKOFF_FACTOR ** (attempt + 1)
                logger.warning("Server error %d, retrying in %ds...", resp.status_code, wait)
                time.sleep(wait)
                continue

            # Client error (4xx except 401/429) — don't retry
            error_body = ""
            try:
                error_body = resp.json().get("error", {}).get("message", resp.text[:500])
            except (ValueError, KeyError, AttributeError):
                error_body = resp.text[:500]
            raise GraphAPIError(resp.status_code, error_body)

        # Exhausted retries
        raise GraphAPIError(
            getattr(last_error, "status_code", 0) if last_error else 0,
            f"Failed after {MAX_RETRIES} retries",
        )

    def get_json(self, endpoint: str, params: dict | None = None) -> dict:
        """GET request returning parsed JSON."""
        resp = self._request_with_retry("GET", endpoint, params=params)
        return resp.json()

    def get_json_all(self, endpoint: str) -> list:
        """GET with automatic @odata.nextLink pagination. Returns all items."""
        items = []
        url = endpoint
        while url:
            data = self.get_json(url)
            items.extend(data.get("value", []))
            url = data.get("@odata.nextLink")
        return items

    def get_text(self, url: str) -> str:
        """GET request returning response body as text (for HTML content)."""
        resp = self._request_with_retry("GET", url, accept="text/html")
        resp.encoding = "utf-8"
        return resp.text

    def get_binary(self, url: str) -> bytes:
        """GET request returning binary content (images, attachments)."""
        resp = self._request_with_retry("GET", url, accept="application/octet-stream")
        return resp.content
