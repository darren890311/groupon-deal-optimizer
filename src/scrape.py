from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright

from src.config import RAW_HTML_DIR

USER_AGENT = (
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


def cached_html_path(slug: str) -> Path:
    return RAW_HTML_DIR / f"{slug}.html"


def fetch_html(url: str, slug: str, force: bool = False, timeout_ms: int = 30000) -> str:
    cache_path = cached_html_path(slug)
    if cache_path.exists() and not force:
        return cache_path.read_text(encoding="utf-8")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1440, "height": 900},
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

            html = page.content()
        finally:
            context.close()
            browser.close()

    cache_path.write_text(html, encoding="utf-8")
    return html
