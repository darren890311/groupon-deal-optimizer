from typing import Any

import anthropic
from pydantic import BaseModel, Field
from tavily import TavilyClient

from src.config import RESEARCH_MODEL, TAVILY_API_KEY


class ResearchQuery(BaseModel):
    category: str = Field(description="One of: competitor_pricing, reputation, category_benchmark, content_gap")
    query: str = Field(description="The search query string for Tavily")


class ResearchPlan(BaseModel):
    queries: list[ResearchQuery] = Field(description="5-7 targeted search queries covering all four categories")


def generate_queries(client: anthropic.Anthropic, audit: dict[str, Any]) -> list[ResearchQuery]:
    title = audit.get("title") or "(unknown)"
    merchant = audit.get("merchant_name") or "(unknown)"
    city = audit.get("city") or "(unknown)"
    category = audit.get("category") or "(unknown)"
    description = (audit.get("description") or "")[:500]

    user_prompt = f"""Generate 5-7 web search queries to research this Groupon deal. Cover all four categories:

1. competitor_pricing: What competitors charge for the same/similar service in the same city
2. reputation: Yelp/Google reviews of this merchant — what customers say
3. category_benchmark: Typical discount ranges and pricing for this category
4. content_gap: Specific concerns or questions customers have about this category that the deal page might not address

Deal:
- Title: {title}
- Merchant: {merchant}
- City: {city}
- Category path: {category}
- Description: {description}

Make each query specific and likely to surface concrete pricing or review data. Use the merchant and city names where relevant."""

    response = client.messages.parse(
        model=RESEARCH_MODEL,
        max_tokens=2000,
        messages=[{"role": "user", "content": user_prompt}],
        output_format=ResearchPlan,
    )
    return response.parsed_output.queries


def run_tavily_searches(queries: list[ResearchQuery], max_results_per_query: int = 4) -> list[dict[str, Any]]:
    if not TAVILY_API_KEY:
        return []
    tavily = TavilyClient(api_key=TAVILY_API_KEY)
    findings: list[dict[str, Any]] = []
    for q in queries:
        try:
            res = tavily.search(query=q.query, max_results=max_results_per_query, search_depth="basic")
        except Exception as e:
            print(f"  Tavily error on '{q.query}': {e}")
            continue
        for item in res.get("results", []):
            findings.append(
                {
                    "category": q.category,
                    "query": q.query,
                    "source_url": item.get("url"),
                    "source_title": item.get("title"),
                    "snippet": item.get("content"),
                }
            )
    return findings


class ReviewThemes(BaseModel):
    positive_themes: list[str] = Field(description="What customers consistently praise (3-5 specific themes with frequency context)")
    negative_themes: list[str] = Field(description="What customers consistently complain about (3-5 specific themes)")
    notable_quotes: list[str] = Field(description="2-4 direct quotes that capture customer sentiment, copied verbatim from the snippets")


def extract_review_themes(
    client: anthropic.Anthropic,
    audit: dict[str, Any],
    findings: list[dict[str, Any]],
) -> ReviewThemes | None:
    review_findings = [f for f in findings if f.get("category") == "reputation"]
    snippets = [f.get("snippet") for f in review_findings if f.get("snippet")]
    if not snippets:
        return None

    text = "\n\n---\n\n".join(snippets[:15])
    merchant = audit.get("merchant_name") or audit.get("title") or "this merchant"

    response = client.messages.parse(
        model=RESEARCH_MODEL,
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": f"""Below are review snippets about {merchant}. Extract recurring themes — what customers consistently praise and complain about. Be concrete: instead of "good service" say "staff remembers regulars by name (mentioned in 3 of 8 snippets)". Quote verbatim where useful.

Snippets:
{text}""",
        }],
        output_format=ReviewThemes,
    )
    return response.parsed_output
