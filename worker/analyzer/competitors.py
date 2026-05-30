"""Competitor discovery — same city, on Groupon.

Strategy (hybrid):
  1. Tavily, constrained to groupon.com, to discover the Groupon *local category*
     page URL for this deal's (category, city) — e.g. /local/chicago/oil-change.
  2. Playwright-scrape that page. It is already city-scoped, so every deal on it
     is a same-city competitor by construction.
  3. Parse the deal cards out of the page's embedded Apollo state
     (__NEXT_DATA__ → __APOLLO_STATE__.ROOT_QUERY.browseDealFeed(...).cards),
     which carries real prices + discounts (no fragile DOM scraping).

The deal under analysis is excluded by slug, remaining cards are marked
`cheaper` relative to it and returned cheapest-first.
"""

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from . import scrape
from .models import Competitor


# --- parse the local category page (pure, network-free) --------------------

def _amount(price_obj: Any) -> int | None:
    """Apollo prices are objects with an integer `amount` in cents."""
    if isinstance(price_obj, dict):
        amt = price_obj.get("amount")
        return amt if isinstance(amt, (int, float)) else None
    return None


def parse_local_cards(html: str) -> list[dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    nd = soup.find("script", id="__NEXT_DATA__")
    if not nd or not nd.string:
        return []
    try:
        data = json.loads(nd.string)
    except json.JSONDecodeError:
        return []

    root = (
        ((data.get("props") or {}).get("pageProps") or {})
        .get("__APOLLO_STATE__", {})
        .get("ROOT_QUERY", {})
    )
    cards: list[Any] = []
    for k, v in root.items():
        if k.startswith("browseDealFeed(") and isinstance(v, dict):
            cards = v.get("cards") or []
            break

    out: list[dict[str, Any]] = []
    for c in cards:
        if not isinstance(c, dict):
            continue
        prices = c.get("prices") or {}
        deal_cents = _amount(prices.get("price"))
        strike_cents = _amount(prices.get("strikeThroughPrice"))
        merchant = c.get("merchant")
        merchant_name = merchant.get("name") if isinstance(merchant, dict) else None
        rating = c.get("rating") if isinstance(c.get("rating"), dict) else {}
        out.append({
            "slug": c.get("id"),
            "url": c.get("url"),
            "title": c.get("title"),
            "merchant": merchant_name,
            "deal_price": deal_cents / 100 if deal_cents is not None else None,
            "original_price": strike_cents / 100 if strike_cents is not None else None,
            "discount_pct": c.get("discountPercentage"),
            "rating": rating.get("value"),
            "rating_count": rating.get("count"),
        })
    return out


# --- discover the local category URL via Tavily ----------------------------

def _category_leaf(category: str | None) -> str:
    """The breadcrumb leaf ('Local > ... > Oil Change' → 'Oil Change')."""
    if not category:
        return ""
    return category.split(">")[-1].strip()


def discover_local_url(category: str | None, city: str | None, tavily_client) -> str | None:
    """Find the best groupon.com/local/<city>/<category> URL for this deal."""
    leaf = _category_leaf(category)
    query = " ".join(p for p in (leaf, city, "Groupon") if p).strip()
    if not query or tavily_client is None:
        return None

    try:
        res = tavily_client.search(
            query=query,
            include_domains=["groupon.com"],
            max_results=8,
            search_depth="basic",
        )
    except Exception as e:
        print(f"  Tavily discover error: {e}")
        return None

    city_token = (city or "").lower().split(",")[0].strip().replace(" ", "-")
    local_urls = [
        r.get("url") for r in res.get("results", [])
        if r.get("url") and "/local/" in urlparse(r["url"]).path
    ]
    if not local_urls:
        return None
    # Prefer a URL whose path mentions this city.
    for u in local_urls:
        if city_token and city_token in urlparse(u).path.lower():
            return u
    return local_urls[0]


# --- orchestrator ----------------------------------------------------------

def find_competitors(
    category: str | None,
    city: str | None,
    *,
    exclude_slug: str | None,
    deal_price: float | None,
    tavily_client,
    max_n: int = 5,
    cache_dir: str | Path | None = None,
) -> list[Competitor]:
    local_url = discover_local_url(category, city, tavily_client)
    if not local_url:
        return []

    try:
        html = scrape.fetch_html(local_url, cache_dir=cache_dir)
    except Exception as e:
        print(f"  competitor page scrape failed ({local_url}): {e}")
        return []

    cards = parse_local_cards(html)
    competitors: list[Competitor] = []
    for c in cards:
        if exclude_slug and c.get("slug") == exclude_slug:
            continue
        if c.get("deal_price") is None:
            continue
        cheaper = (
            deal_price is not None and c["deal_price"] < deal_price
        )
        competitors.append(Competitor(
            merchant=c.get("merchant"),
            title=c.get("title"),
            price=c.get("deal_price"),
            discount_pct=c.get("discount_pct"),
            url=c.get("url"),
            cheaper=cheaper,
        ))

    competitors.sort(key=lambda x: (x.price is None, x.price))
    return competitors[:max_n]


# --- standalone demo: python -m analyzer.competitors "<category>" "<city>" ---

def _demo() -> int:
    import sys

    from dotenv import load_dotenv
    load_dotenv()
    from tavily import TavilyClient
    import os

    category = sys.argv[1] if len(sys.argv) > 1 else "Oil Change"
    city = sys.argv[2] if len(sys.argv) > 2 else "Chicago"
    exclude = sys.argv[3] if len(sys.argv) > 3 else None
    deal_price = float(sys.argv[4]) if len(sys.argv) > 4 else None

    cache_dir = Path(__file__).resolve().parents[1] / "explore_cache"
    tavily = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])

    comps = find_competitors(
        category, city,
        exclude_slug=exclude, deal_price=deal_price,
        tavily_client=tavily, cache_dir=cache_dir,
    )
    print(json.dumps([c.model_dump() for c in comps], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_demo())
