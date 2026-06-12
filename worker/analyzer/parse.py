"""Turn a Groupon deal HTML page into a structured audit dict.

Field-level extractors live in parse_helpers. This module is the orchestrator.
(The v1 mobile-vs-desktop comparator was dropped - v2 is single-deal, desktop only.)
"""

import re
from typing import Any

from bs4 import BeautifulSoup

from .parse_helpers import (
    collect_jsonld,
    count_scripts,
    extract_address,
    extract_alt_text,
    extract_breadcrumbs,
    extract_faqs,
    extract_fine_print,
    extract_highlights,
    extract_prices_from_next_data,
    extract_prices_from_variants,
    find_business,
    find_jsonld,
    list_schema_types,
    money,
    text,
)


def parse_audit(html: str, url: str) -> dict[str, Any]:
    soup = BeautifulSoup(html, "lxml")
    blocks = collect_jsonld(soup)

    product = find_jsonld(blocks, "ProductGroup") or find_jsonld(blocks, "Product") or {}
    business = find_business(blocks)

    title = (
        product.get("name")
        or text(soup.select_one("h1"))
        or (soup.find("meta", property="og:title") or {}).get("content")
    )
    h1 = soup.select_one("h1")
    subtitle = None
    if h1:
        sib = h1.find_next_sibling()
        if sib:
            subtitle = text(sib)

    merchant = None
    brand = product.get("brand")
    if isinstance(brand, dict):
        merchant = brand.get("name")
    elif isinstance(brand, str):
        merchant = brand
    if not merchant and business:
        merchant = business.get("name")

    description = product.get("description") or (
        (soup.find("meta", attrs={"name": "description"}) or {}).get("content")
    )

    # Prefer the Next.js DealOption pricing (true strike-through anchor); fall
    # back to JSON-LD only if it's absent, since JSON-LD mis-reports promo deals.
    prices = extract_prices_from_next_data(soup)
    if not prices:
        variants = product.get("hasVariant") or []
        prices = extract_prices_from_variants(variants if isinstance(variants, list) else [])
    if not prices and isinstance(product.get("offers"), (dict, list)):
        offer = product["offers"]
        if isinstance(offer, list):
            offer = offer[0] if offer else {}
        if isinstance(offer, dict):
            list_price = money(offer.get("price"))
            spec = offer.get("priceSpecification") or {}
            deal_price = money(spec.get("price")) if isinstance(spec, dict) else None
            discount_pct = None
            if list_price and deal_price and list_price > 0 and deal_price < list_price:
                discount_pct = round((1 - deal_price / list_price) * 100, 1)
            prices = [{
                "label": offer.get("name") or "Default",
                "original_price": list_price,
                "deal_price": deal_price or list_price,
                "discount_pct": discount_pct,
            }]

    aggregate = product.get("aggregateRating") or {}
    if not aggregate and business:
        aggregate = business.get("aggregateRating") or {}
    rating = None
    review_count = None
    if isinstance(aggregate, dict):
        try:
            rv = aggregate.get("ratingValue")
            rating = float(rv) if rv is not None else None
        except (TypeError, ValueError):
            pass
        try:
            rc = aggregate.get("reviewCount") or aggregate.get("ratingCount")
            review_count = int(rc) if rc is not None else None
        except (TypeError, ValueError):
            pass

    review_list = product.get("reviews") or product.get("review") or []
    reviews_out: list[dict[str, Any]] = []
    if isinstance(review_list, list):
        for r in review_list[:10]:
            if not isinstance(r, dict):
                continue
            rating_val = None
            rr = r.get("reviewRating")
            if isinstance(rr, dict):
                try:
                    rating_val = float(rr.get("ratingValue")) if rr.get("ratingValue") is not None else None
                except (TypeError, ValueError):
                    pass
            author = r.get("author")
            if isinstance(author, dict):
                author = author.get("name")
            reviews_out.append({
                "rating": rating_val,
                "quote": r.get("reviewBody") or r.get("description"),
                "author": author,
                "date": r.get("datePublished"),
            })

    crumbs = extract_breadcrumbs(blocks)
    category = " > ".join(crumbs) if crumbs else None
    city, region, street = extract_address(business)
    faqs = extract_faqs(blocks)
    highlights = extract_highlights(soup)
    fine_print = extract_fine_print(soup)

    body_text = soup.get_text(" ", strip=True)
    bought_label = None
    bought_match = re.search(r"([\d,]+\+?\s*bought)", body_text, re.IGNORECASE)
    if bought_match:
        bought_label = bought_match.group(1)

    images = soup.find_all("img")
    image_count = sum(1 for img in images if img.get("src") or img.get("data-src"))

    h1s = [text(h) for h in soup.find_all("h1") if text(h)]
    h2s = [text(h) for h in soup.find_all("h2") if text(h)][:25]
    meta_title = text(soup.find("title"))
    meta_desc = (soup.find("meta", attrs={"name": "description"}) or {}).get("content")

    body_lower = body_text.lower()
    urgency_signals = [
        kw for kw in [
            "selling fast", "limited time", "almost gone", "ends soon",
            "only a few left", "limited supply", "today only", "hurry",
        ]
        if kw in body_lower
    ]
    quantity_left_mentions = [
        m.group(1) or m.group(2)
        for m in re.finditer(r"only\s+(\d+)\s+(?:left|remaining)|(\d+)\s+left\b", body_lower)
    ]
    has_countdown_widget = (
        bool(soup.find(attrs={"class": re.compile(r"countdown|timer", re.I)}))
        or bool(soup.find(attrs={"data-countdown": True}))
    )

    trust_signals = {
        "has_rating": rating is not None,
        "has_review_count": review_count is not None,
        "has_bought_label": bought_label is not None,
        "has_guarantee_text": "groupon guarantee" in body_lower or "money back" in body_lower,
    }

    alt_text_coverage, alt_text_sample = extract_alt_text(soup)
    script_counts = count_scripts(soup)
    schema_types = list_schema_types(blocks)

    return {
        "url": url,
        "title": title,
        "subtitle": subtitle,
        "merchant_name": merchant,
        "category": category,
        "breadcrumbs": crumbs,
        "city": city,
        "region": region,
        "address": street,
        "description": description,
        "highlights": highlights,
        "fine_print": fine_print,
        "prices": prices,
        "rating": rating,
        "review_count": review_count,
        "bought_label": bought_label,
        "reviews": reviews_out,
        "faqs": faqs,
        "image_count": image_count,
        "alt_text_coverage": alt_text_coverage,
        "alt_text_sample": alt_text_sample,
        "script_counts": script_counts,
        "schema_types": schema_types,
        "seo": {
            "meta_title": meta_title,
            "meta_description": meta_desc,
            "h1": h1s,
            "h2": h2s,
        },
        "urgency_signals": urgency_signals,
        "has_countdown_widget": has_countdown_widget,
        "quantity_left_mentions": quantity_left_mentions,
        "trust_signals": trust_signals,
    }
