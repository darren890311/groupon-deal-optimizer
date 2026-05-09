import json
from pathlib import Path
from typing import Any

from src.synthesize import OptimizationProposal


def write_audit(out_dir: Path, audit: dict[str, Any]) -> None:
    (out_dir / "audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "audit.md").write_text(_audit_to_markdown(audit), encoding="utf-8")


def write_research(
    out_dir: Path, findings: list[dict[str, Any]], review_themes: dict[str, Any] | None
) -> None:
    (out_dir / "research.md").write_text(_research_to_markdown(findings, review_themes), encoding="utf-8")
    (out_dir / "research.json").write_text(
        json.dumps({"findings": findings, "review_themes": review_themes}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_proposal(out_dir: Path, proposal: OptimizationProposal) -> None:
    (out_dir / "proposal.md").write_text(_proposal_to_markdown(proposal), encoding="utf-8")
    (out_dir / "proposal.json").write_text(proposal.model_dump_json(indent=2), encoding="utf-8")


def _audit_to_markdown(a: dict[str, Any]) -> str:
    lines = [f"# Deal Audit: {a.get('title') or '(no title)'}", ""]
    lines.append(f"- **URL:** {a.get('url')}")
    lines.append(f"- **Merchant:** {a.get('merchant_name')}")
    lines.append(f"- **Location:** {a.get('city')}, {a.get('region')}")
    lines.append(f"- **Category path:** {a.get('category')}")
    lines.append(f"- **Rating:** {a.get('rating')} ({a.get('review_count')} reviews)")
    lines.append(f"- **Bought label:** {a.get('bought_label')}")
    lines.append(f"- **Image count:** {a.get('image_count')}")
    lines.append("")
    if a.get("subtitle"):
        lines.append(f"**Subtitle:** {a['subtitle']}")
        lines.append("")
    if a.get("description"):
        lines.append("## Description")
        lines.append(a["description"])
        lines.append("")
    if a.get("prices"):
        lines.append("## Pricing")
        for p in a["prices"]:
            disc = f" ({p.get('discount_pct')}% off)" if p.get("discount_pct") is not None else ""
            lines.append(f"- {p.get('label')}: ${p.get('deal_price')} (was ${p.get('original_price')}){disc}")
        lines.append("")
    if a.get("highlights"):
        lines.append("## Highlights")
        lines.extend(f"- {h}" for h in a["highlights"])
        lines.append("")
    if a.get("fine_print"):
        lines.append("## Fine Print")
        lines.append(a["fine_print"])
        lines.append("")
    if a.get("reviews"):
        lines.append("## Sample Reviews")
        for r in a["reviews"][:5]:
            rating = r.get("rating") or "?"
            lines.append(f"- ({rating}★) {r.get('quote')}")
        lines.append("")
    seo = a.get("seo") or {}
    lines.append("## SEO")
    lines.append(f"- Meta title: {seo.get('meta_title')}")
    lines.append(f"- Meta description: {seo.get('meta_description')}")
    lines.append(f"- H1s: {seo.get('h1')}")
    lines.append(f"- H2s: {seo.get('h2')}")
    lines.append("")
    lines.append("## Signals")
    lines.append(f"- Trust: {a.get('trust_signals')}")
    lines.append(f"- Urgency: {a.get('urgency_signals')}")
    return "\n".join(lines)


def _research_to_markdown(findings: list[dict[str, Any]], themes: dict[str, Any] | None) -> str:
    lines = ["# Competitive & Market Research", ""]
    if themes:
        lines.append("## Review themes")
        if themes.get("positive_themes"):
            lines.append("**Positive:**")
            lines.extend(f"- {t}" for t in themes["positive_themes"])
        if themes.get("negative_themes"):
            lines.append("\n**Negative:**")
            lines.extend(f"- {t}" for t in themes["negative_themes"])
        if themes.get("notable_quotes"):
            lines.append("\n**Notable quotes:**")
            lines.extend(f"> {q}" for q in themes["notable_quotes"])
        lines.append("")
    by_cat: dict[str, list[dict[str, Any]]] = {}
    for f in findings:
        by_cat.setdefault(f.get("category") or "other", []).append(f)
    for cat in ("competitor_pricing", "reputation", "category_benchmark", "content_gap", "other"):
        items = by_cat.get(cat, [])
        if not items:
            continue
        lines.append(f"## {cat}")
        for f in items:
            lines.append(f"### {f.get('source_title') or 'Source'}")
            lines.append(f"- URL: {f.get('source_url')}")
            lines.append(f"- Query: _{f.get('query')}_")
            snippet = (f.get("snippet") or "").strip()
            if snippet:
                lines.append(f"\n> {snippet}")
            lines.append("")
    return "\n".join(lines)


def _proposal_to_markdown(p: OptimizationProposal) -> str:
    lines = ["# Optimization Proposal", ""]
    lines.append("## Executive summary")
    lines.append(p.executive_summary)
    lines.append("")
    lines.append("## Competitive positioning")
    lines.append(p.competitive_positioning)
    lines.append("")
    lines.append("## Recommendations")
    sorted_recs = sorted(p.recommendations, key=lambda r: r.priority)
    for i, r in enumerate(sorted_recs, 1):
        lines.append(f"### {i}. [{r.field}] (priority {r.priority})")
        lines.append(f"**Current:** {r.current_value}")
        lines.append("")
        lines.append(f"**Proposed:** {r.proposed_value}")
        lines.append("")
        lines.append(f"**Why:** {r.rationale}")
        lines.append("")
        lines.append(f"**Evidence:** {r.evidence}")
        lines.append("")
        lines.append(f"**Expected impact:** {r.expected_impact}")
        lines.append("")
    if p.open_questions:
        lines.append("## Open questions for the merchant / ops")
        lines.extend(f"- {q}" for q in p.open_questions)
    return "\n".join(lines)
