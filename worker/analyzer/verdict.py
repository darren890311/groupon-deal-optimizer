"""Final verdict — the one screen the shopper acts on.

Two halves, by design:
  - Badges are computed deterministically from the data (price / discount /
    reputation), so the visual signal never drifts with LLM phrasing.
  - The narrative (worth_buying, one-liner, recommended action) is written by
    Claude (Sonnet) from those same signals, so it can be nuanced — e.g. "price
    is fair but the discount is fake, book direct" rather than a rigid template.
All output is English.
"""

from typing import Literal

import anthropic
from pydantic import BaseModel, Field

from .competitors import like_for_like_range
from .config import SONNET_MODEL
from .models import Badge, Competitor, Deal, DirectBooking, Reputation, Verdict


def _min_deal_price(deal: Deal) -> float | None:
    prices = [t.deal for t in deal.prices if t.deal is not None]
    return min(prices) if prices else None


def compute_badges(deal: Deal, competitors: list[Competitor], reputation: Reputation) -> list[Badge]:
    badges: list[Badge] = []

    # --- discount ---------------------------------------------------------
    dv = deal.discount_verdict
    if dv == "exaggerated":
        adv = deal.advertised_discount_pct
        act = deal.actual_max_discount_pct or 0
        label = f"Discount exaggerated — {adv:.0f}% claimed, {act:.0f}% real" if adv else "Discount exaggerated"
        badges.append(Badge(type="discount", status="bad", label=label))
    elif dv == "honest":
        badges.append(Badge(type="discount", status="ok", label="Discount is genuine"))
    else:  # none
        badges.append(Badge(type="discount", status="warn", label="No real discount on offer"))

    # --- price (vs like-for-like competitors) -----------------------------
    rng = like_for_like_range(competitors)
    price = _min_deal_price(deal)
    if rng and price is not None:
        lo, hi = rng
        rng_str = f"${lo:.0f}" if lo == hi else f"${lo:.0f}-${hi:.0f}"
        if price <= hi:
            badges.append(Badge(type="price", status="ok",
                                label=f"Price is fair for the service ({rng_str} elsewhere)"))
        else:
            badges.append(Badge(type="price", status="bad",
                                label=f"Above comparable deals ({rng_str} for the same service)"))
    else:
        badges.append(Badge(type="price", status="warn",
                            label="Couldn't verify price against comparable deals"))

    # --- reputation (external vs Groupon) ---------------------------------
    gv = reputation.gap_verdict
    src = reputation.external_source or "other platforms"
    if gv == "external_lower":
        badges.append(Badge(type="reputation", status="bad",
                            label=f"Rated lower on {src} than on Groupon"))
    elif gv == "external_higher":
        badges.append(Badge(type="reputation", status="ok",
                            label=f"Rated higher on {src} (small Groupon sample)"))
    elif gv == "consistent":
        badges.append(Badge(type="reputation", status="ok",
                            label="Ratings consistent across platforms"))
    else:  # insufficient
        badges.append(Badge(type="reputation", status="warn",
                            label="Limited cross-platform review data"))

    return badges


SYSTEM_PROMPT = """You write the final buy/skip verdict for a consumer tool that analyzes a single Groupon deal. A shopper pasted a deal URL; you are given three pre-computed signals about it — discount honesty, price vs like-for-like competitors, and cross-platform reputation — plus the badges already derived from them.

Your job: write the short narrative the shopper acts on. Be direct, honest, plain English. No marketing fluff.

Decide `worth_buying`:
- "yes": the discount is genuine OR the price is clearly fair for the service, and there is no reputation red flag. A confident buy.
- "caution": mixed signals — e.g. the price is fair but the advertised discount is misleading, or the rating picture is muddy. Buyable, but the shopper should know the catch (and may do better booking direct).
- "no": the deal is worse than comparable same-service options (overpriced AND/OR the merchant rates clearly lower elsewhere), often compounded by a fake discount. Steer them away.

`one_liner`: ONE sentence capturing the punchline, in the spirit of "Price is OK but the advertised discount is misleading — consider booking directly via Yelp." Name the specific catch.

`recommended_action`: one concrete next step — e.g. "Buy it — genuine discount and strong reviews", "Book directly via Yelp instead", or "Skip — a comparable full-synthetic change nearby is $40-55".

Ground everything in the numbers given. Never invent prices or ratings. Do not contradict the badges."""


class _VerdictNarrative(BaseModel):
    worth_buying: Literal["yes", "caution", "no"]
    one_liner: str = Field(description="One sentence punchline naming the specific catch")
    recommended_action: str = Field(description="One concrete next step for the shopper")


def synthesize_verdict(
    client: anthropic.Anthropic | None,
    deal: Deal,
    competitors: list[Competitor],
    reputation: Reputation,
    direct_booking: DirectBooking | None = None,
) -> Verdict:
    badges = compute_badges(deal, competitors, reputation)
    if client is None:
        return Verdict(badges=badges)

    rng = like_for_like_range(competitors)
    price = _min_deal_price(deal)
    cheaper_same = [
        c for c in competitors if c.match == "same" and c.cheaper
    ]
    cheaper_lines = "\n".join(
        f"  - {c.merchant}: ${c.price:.0f} ({c.discount_pct:.0f}% off) {c.url}"
        for c in cheaper_same[:3]
    ) or "  (none cheaper at the same service tier)"

    user_content = f"""Deal: {deal.title}  ({deal.merchant}, {deal.city})

Discount: advertised {deal.advertised_discount_pct}% vs actual max {deal.actual_max_discount_pct}% → {deal.discount_verdict}

Price: this deal from ${price}; comparable same-service competitors range {f'${rng[0]:.0f}-${rng[1]:.0f}' if rng else 'unknown (no like-for-like match found)'}.
Cheaper same-service options:
{cheaper_lines}

Reputation: Groupon {reputation.groupon_rating}/{reputation.groupon_reviews} reviews vs {reputation.external_source} {reputation.external_rating}/{reputation.external_reviews} → {reputation.gap_verdict}.
{reputation.summary}

Direct booking: {direct_booking.note if direct_booking else 'not checked'}

Pre-computed badges:
{chr(10).join(f'  - [{b.status}] {b.type}: {b.label}' for b in badges)}

Write the verdict narrative."""

    try:
        resp = client.messages.parse(
            model=SONNET_MODEL,
            max_tokens=1000,
            system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user_content}],
            output_format=_VerdictNarrative,
        )
        n = resp.parsed_output
        return Verdict(
            badges=badges,
            worth_buying=n.worth_buying,
            one_liner=n.one_liner,
            recommended_action=n.recommended_action,
        )
    except Exception as e:
        print(f"  verdict synthesis failed: {e}")
        return Verdict(badges=badges)


# --- standalone demo: python -m analyzer.verdict <deal_url> -----------------

def _demo() -> int:
    import json
    import os
    import sys
    from pathlib import Path

    from tavily import TavilyClient

    from . import scrape
    from .competitors import find_competitors
    from .config import TAVILY_API_KEY
    from .pipeline import analyze
    from .reputation import research_reputation

    if len(sys.argv) < 2:
        print("usage: python -m analyzer.verdict <groupon-deal-url>", file=sys.stderr)
        return 2

    deal_url = sys.argv[1]
    analysis = analyze(deal_url, cache_dir=Path(__file__).resolve().parents[2] / "data" / "raw_html")
    d = analysis.deal

    tavily = TavilyClient(api_key=TAVILY_API_KEY or os.environ["TAVILY_API_KEY"])
    client = anthropic.Anthropic()

    deal_price = _min_deal_price(d)
    comps = find_competitors(
        d.category, d.city,
        exclude_slug=scrape.slug_from_url(deal_url), deal_price=deal_price,
        deal_title=d.title, deal_options=[t.label for t in d.prices if t.label],
        tavily_client=tavily, anthropic_client=client,
        cache_dir=Path(__file__).resolve().parents[1] / "explore_cache",
    )
    rep = research_reputation(
        client, tavily, merchant=d.merchant, city=d.city,
        groupon_rating=analysis.reputation.groupon_rating,
        groupon_reviews=analysis.reputation.groupon_reviews,
    )
    verdict = synthesize_verdict(client, d, comps, rep)
    print(json.dumps(verdict.model_dump(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_demo())
