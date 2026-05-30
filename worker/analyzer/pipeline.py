"""Orchestrator: a Groupon URL → a full DealAnalysis.

Stages: scrape → parse → discount → competitors (+ comparability) →
cross-platform reputation → verdict. Each LLM/Tavily stage degrades gracefully
when no client/key is available (so the deal + discount always return).

Clients can be injected (FastAPI shares one set across requests) or are built
lazily from env keys.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import anthropic
from tavily import TavilyClient

from . import competitors, direct, discount, parse, reputation, scrape, verdict
from .config import ANTHROPIC_API_KEY, TAVILY_API_KEY
from .models import Deal, DealAnalysis, Meta, PriceTier, Reputation


def _build_deal(url: str, audit: dict) -> Deal:
    prices = audit.get("prices") or []
    advertised = discount.parse_advertised_discount(audit.get("title"))
    actual = discount.actual_max_discount(prices)
    return Deal(
        url=url,
        title=audit.get("title"),
        merchant=audit.get("merchant_name"),
        city=audit.get("city"),
        category=audit.get("category"),
        advertised_discount_pct=advertised,
        actual_max_discount_pct=actual,
        discount_verdict=discount.classify(advertised, actual),
        prices=[
            PriceTier(
                label=p.get("label"),
                original=p.get("original_price"),
                deal=p.get("deal_price"),
                discount_pct=p.get("discount_pct"),
            )
            for p in prices
        ],
    )


def _default_clients(anthropic_client, tavily_client):
    if anthropic_client is None and ANTHROPIC_API_KEY:
        anthropic_client = anthropic.Anthropic()
    if tavily_client is None and TAVILY_API_KEY:
        tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
    return anthropic_client, tavily_client


def analyze(
    url: str,
    *,
    cache_dir: str | Path | None = None,
    competitor_cache_dir: str | Path | None = None,
    anthropic_client: anthropic.Anthropic | None = None,
    tavily_client=None,
) -> DealAnalysis:
    html = scrape.fetch_html(url, cache_dir=cache_dir)
    audit = parse.parse_audit(html, url)

    deal = _build_deal(url, audit)
    anthropic_client, tavily_client = _default_clients(anthropic_client, tavily_client)

    deal_price = min((t.deal for t in deal.prices if t.deal is not None), default=None)

    # Competitors, reputation and direct-booking are independent (each derives only
    # from the deal), so run them concurrently — they are all I/O-bound (Tavily,
    # Anthropic, Playwright), which releases the GIL. Only the verdict waits on all.
    with ThreadPoolExecutor(max_workers=3) as pool:
        f_comps = pool.submit(
            competitors.find_competitors,
            deal.category, deal.city,
            exclude_slug=scrape.slug_from_url(url),
            deal_price=deal_price,
            deal_title=deal.title,
            deal_options=[t.label for t in deal.prices if t.label],
            tavily_client=tavily_client,
            anthropic_client=anthropic_client,
            cache_dir=competitor_cache_dir,
        )
        f_rep = pool.submit(
            reputation.research_reputation,
            anthropic_client, tavily_client,
            merchant=deal.merchant, city=deal.city,
            groupon_rating=audit.get("rating"),
            groupon_reviews=audit.get("review_count"),
        )
        f_direct = pool.submit(
            direct.check_direct_booking,
            anthropic_client, tavily_client,
            merchant=deal.merchant, city=deal.city,
            category_leaf=competitors._category_leaf(deal.category),
            service=deal.title, deal_price=deal_price,
        )
        comps = f_comps.result()
        rep = f_rep.result()
        direct_booking = f_direct.result()

    verd = verdict.synthesize_verdict(anthropic_client, deal, comps, rep, direct_booking)

    return DealAnalysis(
        deal=deal,
        reputation=rep,
        competitors=comps,
        direct_booking=direct_booking,
        verdict=verd,
        meta=Meta(analyzed_at=datetime.now(timezone.utc).isoformat()),
    )
