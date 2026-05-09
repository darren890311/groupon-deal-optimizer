from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

from src.config import RAW_HTML_DIR

DESKTOP_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
MOBILE_UA = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1"
)


def slug_from_url(url: str) -> str:
    path = urlparse(url).path
    parts = [p for p in path.split("/") if p]
    if "deals" in parts:
        i = parts.index("deals")
        if i + 1 < len(parts):
            return parts[i + 1]
    return parts[-1] if parts else "unknown"


def cached_html_path(slug: str) -> Path:
    return RAW_HTML_DIR / f"{slug}.html"


def cached_mobile_path(slug: str) -> Path:
    return RAW_HTML_DIR / f"{slug}.mobile.html"


def _fetch(
    url: str,
    *,
    user_agent: str,
    viewport: dict,
    is_mobile: bool,
    timeout_ms: int,
) -> str:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=user_agent,
            viewport=viewport,
            device_scale_factor=3 if is_mobile else 1,
            is_mobile=is_mobile,
            has_touch=is_mobile,
            locale="en-US",
        )
        page = context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except PlaywrightTimeout:
                pass

            for selector in [
                "button[aria-label*='close' i]",
                "button[aria-label*='dismiss' i]",
                "[data-testid*='modal'] button",
            ]:
                try:
                    page.locator(selector).first.click(timeout=1500)
                except Exception:
                    pass

            for _ in range(3):
                page.evaluate("window.scrollBy(0, document.body.scrollHeight / 3)")
                page.wait_for_timeout(700)

            return page.content()
        finally:
            context.close()
            browser.close()


def fetch_html(url: str, slug: str, force: bool = False, timeout_ms: int = 30000) -> str:
    cache_path = cached_html_path(slug)
    if cache_path.exists() and not force:
        return cache_path.read_text(encoding="utf-8")
    html = _fetch(
        url,
        user_agent=DESKTOP_UA,
        viewport={"width": 1440, "height": 900},
        is_mobile=False,
        timeout_ms=timeout_ms,
    )
    cache_path.write_text(html, encoding="utf-8")
    return html


def fetch_html_mobile(url: str, slug: str, force: bool = False, timeout_ms: int = 30000) -> str:
    cache_path = cached_mobile_path(slug)
    if cache_path.exists() and not force:
        return cache_path.read_text(encoding="utf-8")
    html = _fetch(
        url,
        user_agent=MOBILE_UA,
        viewport={"width": 390, "height": 844},
        is_mobile=True,
        timeout_ms=timeout_ms,
    )
    cache_path.write_text(html, encoding="utf-8")
    return html
