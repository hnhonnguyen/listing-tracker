from __future__ import annotations

import time

import requests

DEFAULT_USER_AGENT = "listing-tracker/0.1 (+https://github.com/hnhonnguyen/listing-tracker)"


class FetchError(RuntimeError):
    pass


class Fetcher:
    """HTTP client with per-request delay and retries with backoff.

    The delay is measured between consecutive requests, so callers can pass
    the same delay value everywhere without double-sleeping.
    """

    def __init__(self, user_agent: str = DEFAULT_USER_AGENT, timeout: int = 30, retries: int = 2):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = user_agent
        self.timeout = timeout
        self.retries = retries
        self._last_request = 0.0

    def get(self, url: str, delay: float = 0.0) -> str:
        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            wait = self._last_request + delay - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            try:
                response = self.session.get(url, timeout=self.timeout)
                self._last_request = time.monotonic()
                if response.status_code == 200:
                    return response.text
                error = FetchError(f"HTTP {response.status_code} for {url}")
                if response.status_code < 500 and response.status_code != 429:
                    raise error
                last_error = error
            except requests.RequestException as exc:
                self._last_request = time.monotonic()
                last_error = exc
            if attempt < self.retries:
                time.sleep(1.5 * (attempt + 1))
        raise FetchError(f"giving up on {url} after {self.retries + 1} attempts: {last_error}")
