import json
from typing import Any

import anthropic
from pydantic import BaseModel, Field

from src.config import PROPOSAL_MODEL


class Recommendation(BaseModel):
    field: str = Field(description="One of: title, subtitle, pricing_display, highlights, fine_print, missing_content, images, seo_meta_title, seo_meta_description, seo_headings, trust_signals, urgency, competitive_positioning")
    current_value: str = Field(description="What the deal page currently has for this field, quoted concisely. Use 'N/A' if missing.")
    proposed_value: str = Field(description="The specific proposed replacement or addition. Be concrete — write the actual new title, the actual new bullet points, etc.")
    rationale: str = Field(description="Why this change. Reference specific data: 'Yelp reviews mention X 6 times', 'Competitor A charges $Y', etc.")
    evidence: str = Field(description="Direct quote(s) or pricing data point(s) from the audit or research that justify the rec. If no source, say 'inferred from category norms'.")
    priority: int = Field(description="Priority 1 (highest expected impact) to 5 (nice-to-have)", ge=1, le=5)
    expected_impact: str = Field(description="Plain-English impact estimate: 'lift CTR on category pages', 'reduce post-purchase complaints', etc. One sentence.")


class OptimizationProposal(BaseModel):
    executive_summary: str = Field(description="3-5 sentences: what's wrong with this deal page, what would have the biggest impact, what's the key insight from the research")
    competitive_positioning: str = Field(description="One paragraph on how this deal compares to direct alternatives (booking direct, competitors), and how the page should frame that difference")
    recommendations: list[Recommendation] = Field(description="6-12 specific, evidence-backed recommendations ordered by priority")
    open_questions: list[str] = Field(description="0-3 questions for the merchant or ops team that the page can't answer alone (e.g., 'is parking validated?')")


SYSTEM_PROMPT = """You are an expert e-commerce conversion strategist working in the CEO Office at Groupon. Your job is to audit a live Groupon deal page and produce a tight, actionable optimization proposal that a product manager could hand to the merchant or content team and have shipped within a week.

# What "good" looks like

A CEO reading your proposal should walk away saying "yes, ship this." That requires every recommendation to satisfy three tests:

1. **Specific.** Don't say "improve the title" — write the actual new title verbatim. Don't say "add trust signals" — name which one (e.g., "add a 'Free re-treatment within 14 days' badge under the price"). The merchant should be able to copy-paste your proposal into the CMS.

2. **Evidence-backed.** Every recommendation must reference a concrete data point from the audit or research:
   - A quote from a Yelp/Google review ("3 reviews mention 'parking is hard to find' — add a parking note to the fine print")
   - A competitor price ("Salon X around the corner charges $85 for the same service vs. our $120 list price — reframe value, don't just discount further")
   - A category benchmark ("massage deals in this city typically discount 40-55%; this deal discounts 30%, which underperforms category norms")
   - A content gap ("Yelp reviews praise the 'relaxing music and aromatherapy' but the deal page doesn't mention ambiance once")
   Generic advice ("make the title catchier") is worthless.

3. **Prioritized.** Rank recommendations 1 (highest impact) to 5 (nice-to-have). The CEO has limited bandwidth — what are the 2-3 changes that would actually move conversion?

# Voice and length

- Direct. Plain English. No marketing fluff. No hedging.
- Quote review snippets verbatim with double quotes.
- When pricing data is uncertain, say so ("based on 2 competitor data points, may not be representative").
- The executive summary should be 3-5 sentences a CEO can read in 20 seconds and understand the punchline.

# Field taxonomy

Recommendations target a fixed set of fields, defined as follows:

- **title**: The H1 / main deal title. The single biggest lever for both SEO and click-through.
- **subtitle**: The line below the title (often the merchant name or short pitch). Should resolve "what + where" in <80 chars.
- **pricing_display**: How price/savings/value are framed visually and verbally. Includes "was/now" framing, anchor pricing, savings badge, payment plan callouts.
- **highlights**: The "what you get" bulleted list. Each bullet is a benefit the customer cares about.
- **fine_print**: Terms, expiration, restrictions. Vague fine print is a refund/dispute driver — be specific about what's covered, what's not, who's eligible, when it expires.
- **missing_content**: Information the page should add that customers consistently want before purchase but doesn't appear anywhere on the page (parking, kid-friendly, accessibility, what to bring, what to expect, duration, etc.).
- **images**: What imagery would improve conversion. Quality, count, type (interior, before/after, staff, the actual service in progress).
- **seo_meta_title**: The <title> tag.
- **seo_meta_description**: The meta description shown in search results.
- **seo_headings**: H1/H2 structure on the page itself.
- **trust_signals**: Ratings, review count, "X bought" badges, guarantees, satisfaction promises, certifications.
- **urgency**: "Selling fast", limited inventory, expiry countdown — used judiciously and only when truthful.
- **competitive_positioning**: How the deal frames itself vs. alternatives (book direct, competitor coupon, competitor on Groupon).

When suggesting a rec for a field, the `current_value` should be the page's current value for that field (or "N/A" if missing entirely). The `proposed_value` should be the literal replacement or addition.

# What NOT to do

- **No generic advice.** "Use better images" is not a recommendation. "Add a before/after image of the [specific service the merchant offers], because Yelp reviewers describe results in detail but the page only shows stock interior shots" is a recommendation.
- **Don't invent data.** If the research turned up no competitor pricing data, say so in the rationale and rely on category norms or content gaps instead. Never fabricate a price or quote.
- **Don't recommend things the audit shows are already present.** If the page already has "X bought", don't propose adding it.
- **Don't propose deeper discounting as the answer to weak conversion** unless the research shows the deal is materially overpriced vs. the market. Most of the time, the answer is reframing value, not lowering the price.
- **No more than 12 recommendations.** Cull mercilessly. Five excellent recs beat twelve mediocre ones.

# Output

Return a structured `OptimizationProposal`. Every recommendation must include `evidence` — a verbatim quote or specific data point from the audit/research. If no specific source supports a rec, the `evidence` field should say "inferred from category norms" and the rec should reflect a defensible category-level pattern, not a hunch.

Remember: the goal is for a CEO to read the executive summary, glance at the top 3 recs, and say "yes, do this."
"""


def synthesize_proposal(
    client: anthropic.Anthropic,
    audit: dict[str, Any],
    findings: list[dict[str, Any]],
    review_themes: dict[str, Any] | None,
) -> OptimizationProposal:
    audit_compact = _compact_audit(audit)
    findings_text = _format_findings(findings)
    themes_text = _format_themes(review_themes)

    user_content = f"""# Deal audit (scraped from the live page)

```json
{json.dumps(audit_compact, ensure_ascii=False, indent=2)}
```

# Competitive and merchant research (Tavily web search)

{findings_text}

# Review themes (extracted from the research above)

{themes_text}

---

Write the optimization proposal. Reference specific data points from the audit and research above. Quote review snippets verbatim. Order recommendations by expected impact."""

    response = client.messages.parse(
        model=PROPOSAL_MODEL,
        max_tokens=16000,
        thinking={"type": "adaptive"},
        output_config={"effort": "high"},
        system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user_content}],
        output_format=OptimizationProposal,
    )

    if response.usage:
        print(
            f"    [usage] in={response.usage.input_tokens} "
            f"cached_read={response.usage.cache_read_input_tokens} "
            f"cached_write={response.usage.cache_creation_input_tokens} "
            f"out={response.usage.output_tokens}"
        )

    return response.parsed_output


def _compact_audit(audit: dict[str, Any]) -> dict[str, Any]:
    return {
        "url": audit.get("url"),
        "title": audit.get("title"),
        "subtitle": audit.get("subtitle"),
        "merchant_name": audit.get("merchant_name"),
        "category": audit.get("category"),
        "city": audit.get("city"),
        "region": audit.get("region"),
        "description": (audit.get("description") or "")[:1500],
        "highlights": audit.get("highlights"),
        "fine_print": (audit.get("fine_print") or "")[:1500],
        "prices": audit.get("prices"),
        "rating": audit.get("rating"),
        "review_count": audit.get("review_count"),
        "bought_label": audit.get("bought_label"),
        "reviews_sample": [
            {"rating": r.get("rating"), "quote": (r.get("quote") or "")[:400]}
            for r in (audit.get("reviews") or [])[:5]
        ],
        "image_count": audit.get("image_count"),
        "seo": audit.get("seo"),
        "urgency_signals": audit.get("urgency_signals"),
        "trust_signals": audit.get("trust_signals"),
    }


def _format_findings(findings: list[dict[str, Any]]) -> str:
    if not findings:
        return "_No research findings available._"
    by_cat: dict[str, list[dict[str, Any]]] = {}
    for f in findings:
        by_cat.setdefault(f.get("category") or "other", []).append(f)
    lines = []
    for cat in ("competitor_pricing", "reputation", "category_benchmark", "content_gap"):
        items = by_cat.get(cat, [])
        if not items:
            continue
        lines.append(f"## {cat}")
        for f in items[:8]:
            snippet = (f.get("snippet") or "").strip().replace("\n", " ")
            if len(snippet) > 500:
                snippet = snippet[:500] + "..."
            lines.append(f"- **{f.get('source_title') or 'Source'}** ({f.get('source_url')})")
            lines.append(f"  Query: _{f.get('query')}_")
            lines.append(f"  > {snippet}")
        lines.append("")
    return "\n".join(lines)


def _format_themes(review_themes: dict[str, Any] | None) -> str:
    if not review_themes:
        return "_No review themes extracted (insufficient review data)._"
    parts = []
    if review_themes.get("positive_themes"):
        parts.append("**Positive:**")
        parts.extend(f"- {t}" for t in review_themes["positive_themes"])
    if review_themes.get("negative_themes"):
        parts.append("\n**Negative:**")
        parts.extend(f"- {t}" for t in review_themes["negative_themes"])
    if review_themes.get("notable_quotes"):
        parts.append("\n**Notable quotes:**")
        parts.extend(f"> {q}" for q in review_themes["notable_quotes"])
    return "\n".join(parts)
