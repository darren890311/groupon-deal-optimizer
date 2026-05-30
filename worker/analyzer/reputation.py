"""Cross-platform reputation — does this merchant rate higher/lower elsewhere?

Groupon's on-page rating is often a thin, self-selected sample. We pull the
merchant's rating from external review sites (Yelp/Google) via Tavily, then let
Claude (Sonnet) extract the external rating and judge the gap vs Groupon — so a
shopper sees "5.0 on Yelp vs 3.5 on Groupon (only 4 reviews)" instead of trusting
a tiny on-platform sample.
"""

from typing import Any, Literal

import anthropic
from pydantic import BaseModel, Field

from .config import SONNET_MODEL
from .models import Reputation


def _gather_snippets(tavily_client, merchant: str, city: str | None) -> list[str]:
    if tavily_client is None:
        return []
    query = " ".join(p for p in (merchant, city, "Yelp Google reviews rating") if p)
    try:
        res = tavily_client.search(query=query, max_results=6, search_depth="basic")
    except Exception as e:
        print(f"  Tavily reputation error: {e}")
        return []
    snippets = []
    for item in res.get("results", []):
        title = item.get("title") or ""
        content = item.get("content") or ""
        if content:
            snippets.append(f"[{title}] {content}")
    return snippets


class _ReputationExtract(BaseModel):
    external_rating: float | None = Field(default=None, description="Rating on the external platform, only if explicitly stated")
    external_reviews: int | None = Field(default=None, description="Review count on that platform, only if explicitly stated")
    external_source: str | None = Field(default=None, description="The platform name, e.g. 'Yelp' or 'Google'")
    gap_verdict: Literal["external_higher", "external_lower", "consistent", "insufficient"]
    summary: str = Field(description="One or two sentences in English a shopper can act on")


def research_reputation(
    anthropic_client: anthropic.Anthropic | None,
    tavily_client,
    *,
    merchant: str | None,
    city: str | None,
    groupon_rating: float | None,
    groupon_reviews: int | None,
) -> Reputation:
    base = Reputation(groupon_rating=groupon_rating, groupon_reviews=groupon_reviews)
    if not merchant or anthropic_client is None:
        return base

    snippets = _gather_snippets(tavily_client, merchant, city)
    if not snippets:
        base.summary = "No external review data found to compare against the Groupon rating."
        return base

    snippet_block = "\n\n---\n\n".join(snippets[:8])
    groupon_desc = (
        f"{groupon_rating} stars from {groupon_reviews} reviews"
        if groupon_rating is not None else "no rating shown"
    )
    prompt = f"""The merchant is "{merchant}"{f' in {city}' if city else ''}. On Groupon this merchant shows {groupon_desc}.

Below are web search snippets about this merchant from review sites (Yelp, Google, etc.).

1. Extract the merchant's rating on the most authoritative external platform you can find (prefer Yelp or Google): the rating value, its review count, and the platform name. Use ONLY numbers explicitly stated in the snippets — if none is clearly about THIS merchant, leave them null.
2. Classify gap_verdict comparing external vs Groupon:
   - "external_higher": external rating is clearly higher than Groupon's (about 0.3 stars or more).
   - "external_lower": external is clearly lower.
   - "consistent": within ~0.3 stars.
   - "insufficient": no reliable external rating for this merchant was found.
3. Write a one-to-two sentence English summary a shopper can act on (call out small Groupon sample size, or a genuine quality gap).

Do not invent ratings or review counts.

Snippets:
{snippet_block}"""

    try:
        resp = anthropic_client.messages.parse(
            model=SONNET_MODEL,
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
            output_format=_ReputationExtract,
        )
        ext = resp.parsed_output
    except Exception as e:
        print(f"  reputation extraction failed: {e}")
        base.summary = "External reputation lookup failed."
        return base

    base.external_rating = ext.external_rating
    base.external_reviews = ext.external_reviews
    base.external_source = ext.external_source
    base.gap_verdict = ext.gap_verdict
    base.summary = ext.summary
    return base


# --- standalone demo: python -m analyzer.reputation <deal_url> --------------

def _demo() -> int:
    import json
    import os
    import sys
    from pathlib import Path

    from tavily import TavilyClient

    from .config import TAVILY_API_KEY
    from .pipeline import analyze

    if len(sys.argv) < 2:
        print("usage: python -m analyzer.reputation <groupon-deal-url>", file=sys.stderr)
        return 2

    deal_url = sys.argv[1]
    analysis = analyze(deal_url, cache_dir=Path(__file__).resolve().parents[2] / "data" / "raw_html")
    d = analysis.deal

    tavily = TavilyClient(api_key=TAVILY_API_KEY or os.environ["TAVILY_API_KEY"])
    client = anthropic.Anthropic()

    rep = research_reputation(
        client, tavily,
        merchant=d.merchant, city=d.city,
        groupon_rating=analysis.reputation.groupon_rating,
        groupon_reviews=analysis.reputation.groupon_reviews,
    )
    print(f"Merchant: {d.merchant} ({d.city})\n")
    print(json.dumps(rep.model_dump(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_demo())
