"""Direct-booking check — is booking the merchant directly (or via their official
site) cheaper than the Groupon voucher?

Service prices are rarely published online, so the honest answer is often "no
public direct price found — the Groupon voucher is likely the cheapest listed
option." When an official/direct price IS stated, we compare it to the deal.
"""

from typing import Literal

import anthropic
from pydantic import BaseModel, Field

from .config import SONNET_MODEL
from .models import DirectBooking


def _gather_snippets(tavily_client, merchant: str, city: str | None, category_leaf: str) -> list[str]:
    if tavily_client is None:
        return []
    query = " ".join(p for p in (merchant, city, category_leaf, "official website price book appointment") if p)
    try:
        res = tavily_client.search(query=query, max_results=5, search_depth="basic")
    except Exception as e:
        print(f"  Tavily direct-booking error: {e}")
        return []
    out = []
    for item in res.get("results", []):
        content = item.get("content") or ""
        if content:
            out.append(f"[{item.get('title') or ''}] ({item.get('url') or ''}) {content}")
    return out


class _DirectExtract(BaseModel):
    direct_price: float | None = Field(default=None, description="Live/sale price to book the SAME-scope ticket directly or via an official reseller, only if explicitly stated; prefer the discounted price over a struck-through one")
    source_url: str | None = Field(default=None, description="URL of the official site / source of the direct price")
    note: str = Field(description="One or two sentences in English advising the shopper")


def _decide_cheaper(direct: float | None, groupon: float | None) -> bool | None:
    """Whether booking direct clearly beats Groupon — decided in code, not by the
    LLM. A small gap (within ~10% or ~$3) is within fee/promo noise → None
    ("too close to call"), so the panel says 'verify' rather than declaring a
    winner on a couple of dollars."""
    if direct is None or groupon is None:
        return None
    if abs(direct - groupon) <= max(0.10 * groupon, 3.0):
        return None
    return direct < groupon


def check_direct_booking(
    anthropic_client: anthropic.Anthropic | None,
    tavily_client,
    *,
    merchant: str | None,
    city: str | None,
    category_leaf: str,
    service: str | None,
    deal_price: float | None,
) -> DirectBooking:
    if not merchant or anthropic_client is None:
        return DirectBooking(note="Direct-booking comparison unavailable.")

    snippets = _gather_snippets(tavily_client, merchant, city, category_leaf)
    if not snippets:
        return DirectBooking(
            note="No public direct-booking price found — the Groupon voucher is likely the cheapest listed option. Call the merchant to confirm."
        )

    price_str = f"${deal_price}" if deal_price is not None else "an unknown amount"
    snippet_block = "\n\n---\n\n".join(snippets[:6])
    prompt = f"""The shopper is considering buying this service on Groupon: "{service}" from "{merchant}"{f' in {city}' if city else ''}, where the Groupon price starts at {price_str}.

Below are web search snippets that may include the merchant's official website or direct-booking prices.

1. A price is only valid if the SNIPPET THAT STATES THE PRICE itself names this exact business ("{merchant}"{f' in {city}' if city else ''}). Critically: an anonymous booking/scheduling page (Acuity, Booksy, Square, Calendly, etc.) that lists a price but does NOT name the business does NOT confirm the price belongs to this merchant — even if it appeared in search results for it. Do not use such a price; leave direct_price null. Likewise a different business name, or the same service in a different city/state, is NOT this merchant. If no snippet that names this exact business states a price, leave direct_price null and say no confirmed direct price was found. Only for a confirmed, named match, extract a direct_price for the SAME product/tier/scope — a smaller or different package (e.g. a 3-attraction pass when this deal is a 5-attraction pass, or a single session when this is a 6-pack) is NOT a valid comparison.
   - Snippet prices are often a LIST / "was" / struck-through / "from" anchor, NOT the live checkout price. If a snippet shows both an original and a discounted/sale price (e.g. "$45.75 $41.15" or "was $45.75, now $41.15"), use the LOWER, current price. Treat any extracted price as approximate. (Whether it counts as cheaper is decided downstream, not by you.)
2. note: one or two sentences in English advising the shopper. If the direct price is within a couple of dollars of Groupon, say it's close and tell them to verify the live checkout price; if clearly lower or higher, say so; if none found, say the Groupon voucher is likely cheapest and to call to confirm. E.g. "Klook lists about $X for the same ticket, within a dollar or two of Groupon — check the live price at checkout", or "The only direct price found is for a smaller package, so it isn't directly comparable."

Do not invent prices, never compare across different businesses or cities, and never compare across different package scopes.

Snippets:
{snippet_block}"""

    try:
        resp = anthropic_client.messages.parse(
            model=SONNET_MODEL,  # subtle "same business + city" matching — Haiku was too loose here
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
            output_format=_DirectExtract,
        )
        ext = resp.parsed_output
    except Exception as e:
        print(f"  direct-booking extraction failed: {e}")
        return DirectBooking(note="Direct-booking comparison failed.")

    return DirectBooking(
        cheaper_than_groupon=_decide_cheaper(ext.direct_price, deal_price),
        note=ext.note,
        source_url=ext.source_url,
    )


# --- standalone demo: python -m analyzer.direct <deal_url> ------------------

def _demo() -> int:
    import json
    import os
    import sys
    from pathlib import Path

    from tavily import TavilyClient

    from .competitors import _category_leaf
    from .config import TAVILY_API_KEY
    from .pipeline import analyze

    if len(sys.argv) < 2:
        print("usage: python -m analyzer.direct <groupon-deal-url>", file=sys.stderr)
        return 2

    deal_url = sys.argv[1]
    analysis = analyze(deal_url, cache_dir=Path(__file__).resolve().parents[2] / "data" / "raw_html",
                       competitor_cache_dir=Path(__file__).resolve().parents[1] / "explore_cache")
    d = analysis.deal
    deal_price = min((t.deal for t in d.prices if t.deal is not None), default=None)

    tavily = TavilyClient(api_key=TAVILY_API_KEY or os.environ["TAVILY_API_KEY"])
    client = anthropic.Anthropic()

    db = check_direct_booking(
        client, tavily,
        merchant=d.merchant, city=d.city,
        category_leaf=_category_leaf(d.category), service=d.title,
        deal_price=deal_price,
    )
    print(f"Merchant: {d.merchant} | Groupon from ${deal_price}\n")
    print(json.dumps(db.model_dump(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_demo())
