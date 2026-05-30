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
    direct_price: float | None = Field(default=None, description="Price to book directly/officially, only if explicitly stated for this merchant")
    cheaper_than_groupon: bool | None = Field(default=None, description="true/false vs the Groupon price; null if no direct price found")
    source_url: str | None = Field(default=None, description="URL of the official site / source of the direct price")
    note: str = Field(description="One or two sentences in English advising the shopper")


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

1. If a snippet states a price to book this service DIRECTLY with the merchant (official site, phone, or walk-in), extract it as direct_price with its source_url. Use only prices explicitly stated for THIS merchant; otherwise leave both null.
2. cheaper_than_groupon: true if a direct/official price is clearly lower than the Groupon price; false if clearly higher or equal; null if no direct price was found.
3. note: one or two sentences in English advising the shopper — e.g. "No public direct price; the Groupon voucher is likely the cheapest listed option — call to confirm" or "The merchant's site lists $X, cheaper than Groupon."

Do not invent prices.

Snippets:
{snippet_block}"""

    try:
        resp = anthropic_client.messages.parse(
            model=SONNET_MODEL,
            max_tokens=800,
            messages=[{"role": "user", "content": prompt}],
            output_format=_DirectExtract,
        )
        ext = resp.parsed_output
    except Exception as e:
        print(f"  direct-booking extraction failed: {e}")
        return DirectBooking(note="Direct-booking comparison failed.")

    return DirectBooking(
        cheaper_than_groupon=ext.cheaper_than_groupon,
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
