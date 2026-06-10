"""Orchestrator: a Groupon URL → a full DealAnalysis.

Stages: scrape → parse → discount → competitors (+ comparability) →
cross-platform reputation → verdict. Each LLM/Tavily stage degrades gracefully
when no client/key is available (so the deal + discount always return).

Clients can be injected (FastAPI shares one set across requests) or are built
lazily from env keys.
"""

import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import anthropic
from tavily import TavilyClient

from . import competitors, direct, discount, parse, reputation, scrape, verdict
from .config import ANTHROPIC_API_KEY, GOOGLE_PLACES_API_KEY, TAVILY_API_KEY, YELP_API_KEY
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
    html: str | None = None,
    cache_dir: str | Path | None = None,
    competitor_cache_dir: str | Path | None = None,
    anthropic_client: anthropic.Anthropic | None = None,
    tavily_client=None,
) -> DealAnalysis:
    timings: dict[str, float] = {}

    def _timed(name, fn, *args, **kwargs):
        """Run fn, recording its wall-clock duration under `name` in `timings`."""
        start = time.perf_counter()
        try:
            return fn(*args, **kwargs)
        finally:
            timings[name] = time.perf_counter() - start

    t_total = time.perf_counter()

    # The browser extension supplies the already-rendered page HTML, so we skip
    # the headless-Chromium fetch entirely (no cold-start, no bot-challenge, no
    # datacenter-IP geography issue). The website posts only a URL, in which case
    # we fall back to Playwright — and retry once if the page came back empty.
    if html:
        audit = parse.parse_audit(html, url)
    else:
        html = _timed("scrape", scrape.fetch_html, url, cache_dir=cache_dir)
        audit = parse.parse_audit(html, url)
        if not audit.get("title") or (not audit.get("prices") and audit.get("rating") is None):
            html = _timed("scrape_retry", scrape.fetch_html, url, cache_dir=cache_dir, force=True)
            audit = parse.parse_audit(html, url)

    deal = _build_deal(url, audit)
    anthropic_client, tavily_client = _default_clients(anthropic_client, tavily_client)

    deal_price = min((t.deal for t in deal.prices if t.deal is not None), default=None)

    # Competitors, reputation and direct-booking are independent (each derives only
    # from the deal), so run them concurrently — they are all I/O-bound (Tavily,
    # Anthropic, Playwright), which releases the GIL. Only the verdict waits on all.
    t_parallel = time.perf_counter()
    with ThreadPoolExecutor(max_workers=3) as pool:
        f_comps = pool.submit(
            _timed, "competitors", competitors.find_competitors,
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
            _timed, "reputation", reputation.research_reputation,
            anthropic_client, tavily_client,
            merchant=deal.merchant, city=deal.city,
            groupon_rating=audit.get("rating"),
            groupon_reviews=audit.get("review_count"),
            places_api_key=GOOGLE_PLACES_API_KEY,
            yelp_api_key=YELP_API_KEY,
        )
        f_direct = pool.submit(
            _timed, "direct", direct.check_direct_booking,
            anthropic_client, tavily_client,
            merchant=deal.merchant, city=deal.city,
            category_leaf=competitors._category_leaf(deal.category),
            service=deal.title, deal_price=deal_price,
        )
        comps = f_comps.result()
        rep = f_rep.result()
        direct_booking = f_direct.result()
    timings["parallel_wall"] = time.perf_counter() - t_parallel

    verd = _timed("verdict", verdict.synthesize_verdict, anthropic_client, deal, comps, rep, direct_booking)

    timings["total"] = time.perf_counter() - t_total
    print("[timing] " + "  ".join(f"{k}={v:.2f}s" for k, v in timings.items()))

    return DealAnalysis(
        deal=deal,
        reputation=rep,
        competitors=comps,
        direct_booking=direct_booking,
        verdict=verd,
        meta=Meta(analyzed_at=datetime.now(timezone.utc).isoformat()),
    )
