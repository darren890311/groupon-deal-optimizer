"""Orchestrator: a Groupon URL → a DealAnalysis.

Milestone 1 fills `deal` (incl. the advertised-vs-actual discount verdict) and
the Groupon side of `reputation`. Competitors, external reputation, direct
booking and the LLM verdict are layered in by later milestones.
"""

from datetime import datetime, timezone
from pathlib import Path

from . import discount, parse, scrape
from .models import Deal, DealAnalysis, Meta, PriceTier, Reputation


def analyze(url: str, *, cache_dir: str | Path | None = None) -> DealAnalysis:
    html = scrape.fetch_html(url, cache_dir=cache_dir)
    audit = parse.parse_audit(html, url)

    prices = audit.get("prices") or []
    advertised = discount.parse_advertised_discount(audit.get("title"))
    actual = discount.actual_max_discount(prices)

    deal = Deal(
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

    reputation = Reputation(
        groupon_rating=audit.get("rating"),
        groupon_reviews=audit.get("review_count"),
    )

    return DealAnalysis(
        deal=deal,
        reputation=reputation,
        meta=Meta(analyzed_at=datetime.now(timezone.utc).isoformat()),
    )
