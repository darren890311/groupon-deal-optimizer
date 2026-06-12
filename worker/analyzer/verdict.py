"""Final verdict - the one screen the shopper acts on.

Two halves, by design:
 - Badges are computed deterministically from the data (price / discount /
    reputation), so the visual signal never drifts with LLM phrasing.
 - The narrative (worth_buying, one-liner, recommended action) is written by
    Claude (Sonnet) from those same signals, so it can be nuanced - e.g. "price
    is fair but the discount is fake, book direct" rather than a rigid template.
All output is English.
"""

from typing import Literal

import anthropic
from pydantic import BaseModel, Field

from .competitors import like_for_like_range
from .config import HAIKU_MODEL, SONNET_MODEL
from .models import Badge, Competitor, Deal, DirectBooking, Reputation, Verdict


def _min_deal_price(deal: Deal) -> float | None:
    prices = [t.deal for t in deal.prices if t.deal is not None]
    return min(prices) if prices else None


def _fmt_range(lo: float, hi: float) -> str:
    return f"${lo:.0f}" if lo == hi else f"${lo:.0f}-${hi:.0f}"


def compute_badges(
    deal: Deal,
    competitors: list[Competitor],
    reputation: Reputation,
    direct_booking: DirectBooking | None = None,
) -> list[Badge]:
    badges: list[Badge] = []

    # --- discount ---------------------------------------------------------
    # Fake anchor: if a confirmed direct price is the same or cheaper than the
    # Groupon price, the headline discount gives no real saving - the "original"
    # is an inflated anchor. This overrides Groupon's internally-honest math.
    entry = _min_deal_price(deal)
    direct_price = direct_booking.direct_price if direct_booking else None
    dv = deal.discount_verdict
    if direct_price is not None and entry is not None and direct_price <= entry:
        badges.append(Badge(type="discount", status="bad",
                            label=f"Not a real deal - direct is ${direct_price:.0f}, same or less"))
    elif dv == "exaggerated":
        adv = deal.advertised_discount_pct
        act = deal.actual_max_discount_pct or 0
        label = f"Discount exaggerated - {adv:.0f}% claimed, {act:.0f}% real" if adv else "Discount exaggerated"
        badges.append(Badge(type="discount", status="bad", label=label))
    elif dv == "honest":
        badges.append(Badge(type="discount", status="ok", label="Discount is genuine"))
    else:  # none
        badges.append(Badge(type="discount", status="warn", label="No real discount on offer"))

    # --- price (tiered: like-for-like → comparable-but-not-identical) -----
    price = _min_deal_price(deal)
    same_rng = like_for_like_range(competitors)
    similar_prices = [c.price for c in competitors if c.match == "similar" and c.price is not None]
    if price is not None and same_rng:
        lo, hi = same_rng
        rng_str = _fmt_range(lo, hi)
        if price <= hi:
            badges.append(Badge(type="price", status="ok",
                                label=f"Price is fair for the service ({rng_str} elsewhere)"))
        else:
            badges.append(Badge(type="price", status="bad",
                                label=f"Above comparable deals ({rng_str} for the same service)"))
    elif price is not None and similar_prices:
        # No exact match - benchmark against similar (not identical) deals, and
        # say so, so a premium for extra features doesn't read as "overpriced".
        lo, hi = min(similar_prices), max(similar_prices)
        rng_str = _fmt_range(lo, hi)
        if price <= hi * 1.10:
            badges.append(Badge(type="price", status="ok",
                                label=f"In line with comparable (not identical) deals ({rng_str})"))
        else:
            badges.append(Badge(type="price", status="warn",
                                label=f"Pricier than comparable (not identical) deals ({rng_str}) - check the extras are worth it"))
    else:
        badges.append(Badge(type="price", status="warn",
                            label="Couldn't verify price against comparable deals"))

    # --- reputation (external vs Groupon) ---------------------------------
    gv = reputation.gap_verdict
    src = "Google" if reputation.google_rating is not None else ("Yelp" if reputation.yelp_rating is not None else "other platforms")
    if reputation.chain:
        badges.append(Badge(type="reputation", status="warn",
                            label="National chain - reviews vary by location"))
    elif gv == "divergent":
        badges.append(Badge(type="reputation", status="warn",
                            label="Ratings disagree sharply across platforms"))
    elif gv == "external_lower":
        badges.append(Badge(type="reputation", status="bad",
                            label=f"Rated lower on {src} than on Groupon"))
    elif gv == "external_higher":
        badges.append(Badge(type="reputation", status="ok",
                            label=f"Rated higher on {src} than on Groupon"))
    elif gv == "consistent":
        badges.append(Badge(type="reputation", status="ok",
                            label="Ratings consistent across platforms"))
    else:  # insufficient
        badges.append(Badge(type="reputation", status="warn",
                            label="Limited cross-platform review data"))

    return badges


SYSTEM_PROMPT = """You write the final buy/skip verdict for a consumer tool that analyzes a single Groupon deal. A shopper pasted a deal URL; you are given three pre-computed signals about it - discount honesty, price vs like-for-like competitors, and cross-platform reputation - plus the badges already derived from them.

Your job: write the short narrative the shopper acts on. Be direct, honest, plain English. No marketing fluff.

The overall verdict (`worth_buying`) is ALREADY DECIDED for you and given in the input below - do not re-decide it. It is "yes" only when all three signals (discount, price, reputation) are good, "no" only when all three are bad, and "caution" otherwise (a single weak signal is caution, not "no"). Your one-liner and action must match the given verdict.

On price: only describe a deal as "overpriced" when it loses to an equivalent ("same") service. If the only similar deals are "similar" (related but a spec difference), do NOT call it overpriced - note that comparable deals run $X-Y and that the higher price may reflect extras this deal includes. Never compare a richer bundle to a barer service as if equal.

`one_liner`: ONE sentence capturing the punchline, in the spirit of "Price is OK but the advertised discount is misleading - consider booking directly via Yelp." Name the specific catch.

`recommended_action`: one concrete next step - e.g. "Buy it - genuine discount and strong reviews", "Book directly via Yelp instead", or "Skip - a comparable full-synthetic change nearby is $40-55".

Wording: this is a consumer tool. In your output, refer to other deals/shops as "similar deals" or "nearby options" - never "competitor" or "competitors".

Ground everything in the numbers given. Never invent prices or ratings. Do not contradict the badges."""


def derive_worth_buying(badges: list[Badge]) -> str:
    """Deterministic verdict from the three signal badges (discount, price,
    reputation): all good → yes, all bad → no, anything in between → caution.
    A single weak signal never drops a deal to "no".
    """
    by_type = {b.type: b.status for b in badges}
    signals = [by_type.get("discount"), by_type.get("price"), by_type.get("reputation")]
    if all(s == "ok" for s in signals):
        return "yes"
    if all(s == "bad" for s in signals):
        return "no"
    return "caution"


class _VerdictNarrative(BaseModel):
    one_liner: str = Field(description="One sentence punchline naming the specific catch")
    recommended_action: str = Field(description="One concrete next step for the shopper")


def synthesize_verdict(
    client: anthropic.Anthropic | None,
    deal: Deal,
    competitors: list[Competitor],
    reputation: Reputation,
    direct_booking: DirectBooking | None = None,
    model: str = HAIKU_MODEL,  # flip to SONNET_MODEL for a slightly richer verdict
) -> Verdict:
    badges = compute_badges(deal, competitors, reputation, direct_booking)
    worth = derive_worth_buying(badges)
    if client is None:
        return Verdict(badges=badges, worth_buying=worth)

    rng = like_for_like_range(competitors)
    price = _min_deal_price(deal)
    if rng:
        price_basis = f"comparable SAME-service deals range {_fmt_range(*rng)}"
    elif any(c.match == "similar" for c in competitors):
        sims = [c.price for c in competitors if c.match == "similar" and c.price is not None]
        price_basis = (f"no exact match found; SIMILAR (not identical) deals range {_fmt_range(min(sims), max(sims))} "
                       "(a higher price here may be justified by extras this deal includes)")
    else:
        price_basis = "no comparable deals found"

    comp_lines = "\n".join(
        f" - [{c.match}] {c.merchant or c.title}: "
        + (f"${c.price:.0f}" if c.price is not None else "price n/a")
        + (f" ({c.discount_pct:.0f}% off)" if c.discount_pct is not None else "")
        + (f" - {c.difference_note}" if c.difference_note else "")
        + (f" {c.url}" if c.cheaper else "")
        for c in competitors[:5]
    ) or "  (no comparable deals found)"

    user_content = f"""Deal: {deal.title}  ({deal.merchant}, {deal.city})

Discount: advertised {deal.advertised_discount_pct}% vs actual max {deal.actual_max_discount_pct}% → {deal.discount_verdict}

Price: this deal from ${price}; {price_basis}.
Similar deals (same city; "same" = equivalent service, "similar" = related but a spec difference):
{comp_lines}

Reputation: Groupon {reputation.groupon_rating}★/{reputation.groupon_reviews} reviews · Google {reputation.google_rating}★/{reputation.google_reviews} · Yelp {reputation.yelp_rating}★/{reputation.yelp_reviews} → {reputation.gap_verdict}.
{reputation.summary}

Direct booking: {direct_booking.note if direct_booking else 'not checked'}

Pre-computed badges:
{chr(10).join(f' - [{b.status}] {b.type}: {b.label}' for b in badges)}

Overall verdict (ALREADY DECIDED - write a one-liner and action consistent with this, do not contradict it): {worth}

Write the verdict narrative."""

    try:
        resp = client.messages.parse(
            model=model,
            max_tokens=1000,
            system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user_content}],
            output_format=_VerdictNarrative,
        )
        n = resp.parsed_output
        return Verdict(
            badges=badges,
            worth_buying=worth,
            one_liner=n.one_liner,
            recommended_action=n.recommended_action,
        )
    except Exception as e:
        print(f"  verdict synthesis failed: {e}")
        return Verdict(badges=badges, worth_buying=worth)


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
