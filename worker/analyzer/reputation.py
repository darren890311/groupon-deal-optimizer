"""Cross-platform reputation — Groupon vs Google vs Yelp.

Groupon's on-page rating is often a thin, self-selected sample. We pull two
external ratings to put it in context:
  - **Google** via the Places API (reliable, structured rating + review count).
  - **Yelp** via Tavily web search + Claude extraction (Yelp exposes its rating
    in search snippets; Google's lives in Maps and isn't reliably searchable).

The gap verdict compares Groupon against the most authoritative external rating
(Google preferred), and is computed deterministically.
"""

import json
import urllib.parse
import urllib.request

import anthropic
from pydantic import BaseModel, Field

from .config import HAIKU_MODEL
from .models import GapVerdict, Reputation


# --- Google rating via Places API (no LLM) ---------------------------------

def _is_chain(merchant: str, places: list[dict]) -> bool:
    """A multi-location chain: several of the top results share the merchant's
    brand name but sit at different addresses (e.g. AMC, Massage Envy). For those
    there is no single 'merchant' rating — picking places[0] would be one random
    branch, so we don't trust it.
    """
    brand = merchant.split()[0].lower() if merchant else ""
    same_brand = [
        p for p in places[:5]
        if ((p.get("displayName") or {}).get("text", "").split() or [""])[0].lower() == brand
    ]
    addrs = {p.get("formattedAddress") for p in same_brand}
    return len(same_brand) >= 3 and len(addrs) >= 3


def _google_places_rating(merchant: str, city: str | None, api_key: str) -> tuple[float | None, int | None, bool]:
    """Return (rating, review_count, is_chain). For a chain, rating/count are
    None — the rating varies by location, so there's no honest single number."""
    if not api_key or not merchant:
        return None, None, False
    query = f"{merchant} {city}".strip() if city else merchant
    req = urllib.request.Request(
        "https://places.googleapis.com/v1/places:searchText",
        # regionCode anchors the search to the US so results don't depend on the
        # caller's IP — without it, a no-city chain name returns nothing from a
        # datacenter IP (Cloud Run) while resolving fine from a US laptop.
        data=json.dumps({"textQuery": query, "regionCode": "US"}).encode(),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.rating,places.userRatingCount",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"  Places API error: {e}")
        return None, None, False
    places = data.get("places") or []
    if not places:
        return None, None, False
    if _is_chain(merchant, places):
        return None, None, True
    p = places[0]
    r, c = p.get("rating"), p.get("userRatingCount")
    return (float(r) if r is not None else None, int(c) if c is not None else None, False)


# --- Yelp rating via Fusion API (no LLM, structured) -----------------------

def _yelp_fusion_rating(merchant: str, city: str | None, api_key: str) -> tuple[float | None, int | None]:
    """Best-match Yelp business for (merchant, city) → (rating, review_count).

    Yelp renders its stars as images, so web snippets carry the review count but
    not the score — the Fusion API is the only reliable source of the number.
    """
    if not api_key or not merchant:
        return None, None
    params = urllib.parse.urlencode({
        "term": merchant,
        "location": city or "United States",
        "limit": 1,
        "sort_by": "best_match",
    })
    req = urllib.request.Request(
        f"https://api.yelp.com/v3/businesses/search?{params}",
        headers={"Authorization": f"Bearer {api_key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except Exception as e:
        print(f"  Yelp Fusion error: {e}")
        return None, None
    businesses = data.get("businesses") or []
    if not businesses:
        return None, None
    b = businesses[0]
    r, c = b.get("rating"), b.get("review_count")
    return (float(r) if r is not None else None, int(c) if c is not None else None)


# --- Yelp rating via Tavily + LLM (fallback when no Fusion key) -------------

def _gather_yelp_snippets(tavily_client, merchant: str, city: str | None) -> list[str]:
    if tavily_client is None:
        return []
    query = " ".join(p for p in (merchant, city, "Yelp rating reviews") if p)
    try:
        res = tavily_client.search(query=query, max_results=6, search_depth="basic")
    except Exception as e:
        print(f"  Tavily reputation error: {e}")
        return []
    out = []
    for item in res.get("results", []):
        content = item.get("content") or ""
        if content:
            out.append(f"[{item.get('title') or ''}] {content}")
    return out


class _YelpExtract(BaseModel):
    yelp_rating: float | None = Field(default=None, description="Yelp star rating, only if explicitly stated for THIS merchant")
    yelp_reviews: int | None = Field(default=None, description="Yelp review count, only if explicitly stated")
    summary: str = Field(description="One or two sentences in English comparing the platforms a shopper can act on")


def _extract_yelp_and_summary(client, merchant, city, groupon_rating, groupon_reviews,
                              google_rating, google_reviews, snippets) -> _YelpExtract | None:
    known = [f"Groupon: {groupon_rating}★ from {groupon_reviews} reviews"]
    if google_rating is not None:
        known.append(f"Google: {google_rating}★ from {google_reviews} reviews (authoritative, from Google Places)")
    prompt = f"""The merchant is "{merchant}"{f' in {city}' if city else ''}.

Ratings already known:
- {chr(10).join('- ' + k for k in known)}

Below are web search snippets, used to find this merchant's YELP rating.
1. Extract the merchant's YELP rating and review count — ONLY if explicitly stated for THIS merchant; otherwise leave both null. Do not invent numbers.
2. Write a one-to-two sentence English summary a shopper can act on, comparing the platforms: note small samples (e.g. few Groupon reviews) and whether the more-reviewed Google/Yelp ratings agree or disagree with Groupon.

Snippets:
{chr(10).join('———' + chr(10) + s for s in snippets[:8]) or '(none)'}"""
    try:
        resp = client.messages.parse(
            model=HAIKU_MODEL, max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
            output_format=_YelpExtract,
        )
        return resp.parsed_output
    except Exception as e:
        print(f"  yelp extraction failed: {e}")
        return None


# --- gap verdict (deterministic) -------------------------------------------

def _compute_gap(groupon: float | None, google: float | None, yelp: float | None) -> GapVerdict:
    """Compare Groupon against the most authoritative external (Google preferred)."""
    primary = google if google is not None else yelp
    if groupon is None or primary is None:
        return "insufficient"
    diff = primary - groupon
    if diff >= 0.3:
        return "external_higher"
    if diff <= -0.3:
        return "external_lower"
    return "consistent"


def _template_summary(gr, grv, gg, ggv, yr, yrv) -> str:
    ext = []
    if gg is not None:
        ext.append(f"Google {gg}★ ({ggv} reviews)")
    if yr is not None:
        ext.append(f"Yelp {yr}★ ({yrv} reviews)")
    if not ext:
        return "No external rating found to compare against the Groupon score."
    return f"Groupon shows {gr}★ from {grv} reviews; elsewhere: " + ", ".join(ext) + "."


class _Summary(BaseModel):
    summary: str = Field(description="One or two sentences in English a shopper can act on")


def _write_summary(client, merchant, city, gr, grv, gg, ggv, yr, yrv) -> str:
    """LLM comparison summary when all ratings are already structured (Google +
    Yelp from their APIs) — no extraction, just a shopper-facing read."""
    lines = [f"Groupon: {gr}★ from {grv} reviews"]
    if gg is not None:
        lines.append(f"Google: {gg}★ from {ggv} reviews")
    if yr is not None:
        lines.append(f"Yelp: {yr}★ from {yrv} reviews")
    prompt = f"""The merchant is "{merchant}"{f' in {city}' if city else ''}. Ratings (all from official sources):
{chr(10).join('- ' + l for l in lines)}

Write a one-to-two sentence English summary a shopper can act on: note small samples (e.g. few Groupon reviews) and whether the larger-sample Google/Yelp ratings agree or disagree with Groupon. Ground every number in the data above; invent nothing."""
    try:
        resp = client.messages.parse(
            model=HAIKU_MODEL, max_tokens=600,
            messages=[{"role": "user", "content": prompt}],
            output_format=_Summary,
        )
        return resp.parsed_output.summary
    except Exception as e:
        print(f"  summary write failed: {e}")
        return ""


# --- orchestrator ----------------------------------------------------------

def research_reputation(
    anthropic_client: anthropic.Anthropic | None,
    tavily_client,
    *,
    merchant: str | None,
    city: str | None,
    groupon_rating: float | None,
    groupon_reviews: int | None,
    places_api_key: str = "",
    yelp_api_key: str = "",
) -> Reputation:
    rep = Reputation(groupon_rating=groupon_rating, groupon_reviews=groupon_reviews)
    if not merchant:
        return rep

    # Google (Places API) — independent of the LLM.
    rep.google_rating, rep.google_reviews, rep.chain = _google_places_rating(merchant, city, places_api_key)

    # National deal (no city) with no single Google location is effectively the
    # same case — ratings vary by branch. Treat it as a chain rather than a bare
    # "no rating found".
    if not rep.chain and rep.google_rating is None and not city:
        rep.chain = True

    # Multi-location / national: no single external rating is meaningful. Don't
    # pull a per-branch Yelp number either — just say so.
    if rep.chain:
        rep.gap_verdict = "insufficient"
        gr = f"{groupon_rating}★ from {groupon_reviews} reviews" if groupon_rating is not None else "the Groupon score above"
        rep.summary = (
            f"{merchant} operates across many locations, so Google and Yelp ratings vary by individual "
            f"branch — there's no single brand-wide score to compare. {gr.capitalize()} reflects this "
            "specific deal; check the rating of the exact location you'd visit before buying."
        )
        return rep

    # Yelp + a comparison summary. Prefer the Fusion API (structured stars);
    # fall back to Tavily + LLM extraction only when no Fusion key is set.
    summary = ""
    if yelp_api_key:
        rep.yelp_rating, rep.yelp_reviews = _yelp_fusion_rating(merchant, city, yelp_api_key)
        if anthropic_client is not None:
            summary = _write_summary(
                anthropic_client, merchant, city, groupon_rating, groupon_reviews,
                rep.google_rating, rep.google_reviews, rep.yelp_rating, rep.yelp_reviews,
            )
    elif anthropic_client is not None:
        snippets = _gather_yelp_snippets(tavily_client, merchant, city)
        ext = _extract_yelp_and_summary(
            anthropic_client, merchant, city, groupon_rating, groupon_reviews,
            rep.google_rating, rep.google_reviews, snippets,
        )
        if ext:
            rep.yelp_rating, rep.yelp_reviews = ext.yelp_rating, ext.yelp_reviews
            summary = ext.summary

    rep.gap_verdict = _compute_gap(groupon_rating, rep.google_rating, rep.yelp_rating)
    rep.summary = summary or _template_summary(
        groupon_rating, groupon_reviews, rep.google_rating, rep.google_reviews,
        rep.yelp_rating, rep.yelp_reviews,
    )
    return rep


# --- standalone demo: python -m analyzer.reputation <deal_url> --------------

def _demo() -> int:
    import os
    import sys
    from pathlib import Path

    from tavily import TavilyClient

    from .config import GOOGLE_PLACES_API_KEY, TAVILY_API_KEY
    from .pipeline import analyze

    if len(sys.argv) < 2:
        print("usage: python -m analyzer.reputation <groupon-deal-url>", file=sys.stderr)
        return 2

    analysis = analyze(sys.argv[1], cache_dir=Path(__file__).resolve().parents[2] / "data" / "raw_html")
    d = analysis.deal
    tavily = TavilyClient(api_key=TAVILY_API_KEY or os.environ["TAVILY_API_KEY"])
    rep = research_reputation(
        anthropic.Anthropic(), tavily,
        merchant=d.merchant, city=d.city,
        groupon_rating=analysis.reputation.groupon_rating,
        groupon_reviews=analysis.reputation.groupon_reviews,
        places_api_key=GOOGLE_PLACES_API_KEY,
    )
    print(f"Merchant: {d.merchant} ({d.city})\n")
    print(json.dumps(rep.model_dump(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_demo())
