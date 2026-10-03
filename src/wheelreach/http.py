"""Minimal HTTP helpers (stdlib only)."""
from __future__ import annotations

import urllib.error
import urllib.request

USER_AGENT = "wheelreach (+https://github.com/hahahahahahahahah6/wheelreach)"


class FetchError(Exception):
    """Raised when an HTTP fetch fails."""


def fetch(url: str, timeout: int = 30) -> tuple[bytes, dict]:
    """GET url. Returns (body, headers dict). Raises FetchError on failure."""
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read(), dict(resp.headers)
    except urllib.error.HTTPError as exc:
        raise FetchError(f"GET {url}: HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise FetchError(f"GET {url}: network error: {exc}") from exc
