"""Playwright fetch of a single Groupon deal page (desktop only).

Stateless: the optional ``cache_dir`` is a dev convenience (reuse pre-scraped
HTML during local iteration). In production the Go layer owns caching.
"""

from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

DESKTOP_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def slug_from_url(url: str) -> str:
    path = urlparse(url).path
    parts = [p for p in path.split("/") if p]
    if "deals" in parts:
        i = parts.index("deals")
        if i + 1 < len(parts):
            return parts[i + 1]
    return parts[-1] if parts else "unknown"


def normalize_url(url: str) -> str:
    """Cache key: drop query (e.g. ?redemptionLocationId=...) and trailing slash."""
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}{p.path.rstrip('/')}"


def _fetch(url: str, *, timeout_ms: int) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=DESKTOP_UA,
            viewport={"width": 1440, "height": 900},
            locale="en-US",
        )
        page = context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            # Groupon server-renders the data we extract (JSON-LD + __NEXT_DATA__)
            # into the initial HTML, so domcontentloaded already has it — a short
            # settle wait covers late hydration. A/B tested ~7x faster than waiting
            # on networkidle + lazy-load scrolls, with identical extracted data.
            page.wait_for_timeout(600)
            return page.content()
        finally:
            context.close()
            browser.close()


def fetch_html(
    url: str,
    *,
    cache_dir: str | Path | None = None,
    force: bool = False,
    timeout_ms: int = 30000,
) -> str:
    slug = slug_from_url(url)
    cache_path = Path(cache_dir) / f"{slug}.html" if cache_dir else None

    if cache_path and cache_path.exists() and not force:
        return cache_path.read_text(encoding="utf-8")

    html = _fetch(url, timeout_ms=timeout_ms)

    if cache_path:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(html, encoding="utf-8")
    return html
