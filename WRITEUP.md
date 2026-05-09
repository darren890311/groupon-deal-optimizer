# Write-up

**Headline finding across the 20-deal sample:** 19 of 20 deals (95%) advertise a headline discount in the title that's materially larger than the actual displayed savings, 5 of 20 (25%) show no discount at all on any price tier, and all 20 are missing at least one core trust signal — every single deal lacks the Groupon Guarantee callout.

## What I built

A Python pipeline turning 20 Groupon URLs into 20 evidence-backed optimization proposals. Five stages, wired through DuckDB so any stage can be re-run independently:

1. **Scrape** — Playwright (Chromium, desktop + mobile UA) → cached HTML
2. **Parse** — BeautifulSoup + JSON-LD (`ProductGroup`, `HealthAndBeautyBusiness`, `BreadcrumbList`, `FAQPage`) → structured audit
3. **Research** — Claude (Sonnet 4.6) generates 5–7 targeted Tavily queries per deal (competitor pricing, reputation, category benchmarks, content gaps)
4. **Theme extraction** — Claude (Sonnet 4.6) extracts recurring review themes with verbatim quotes
5. **Synthesis** — Claude (Opus 4.7, adaptive thinking, `effort: high`) writes the proposal as a structured Pydantic object grounded in audit + research

AI is used as judgment, not summarization: Claude decides what to search for, judges which review themes matter, and writes evidence-cited recommendations. The ~5KB synthesis system prompt is marked with `cache_control: ephemeral`, so the prefix is reused across all 20 deals — verified ~85% input-cost reduction (3,047 cached tokens on 17 of 18 calls). Total spend: ~$3, zero errors. Per-deal outputs (`audit`, `research`, `proposal` × JSON + Markdown) land in `output/<slug>/`; all structured data also persists in `data/groupon.duckdb`.

## What I'd improve with more time

- **Parse highlights/fine_print from `__NEXT_DATA__` (Groupon's embedded React state).** Groupon hides these in 257KB of embedded JSON, not in the rendered DOM. My current heuristic falls back to section header labels ("Need To Know Info"). Mining the Next.js JSON would close this gap and give every proposal a real "current value" baseline for those fields.
- **Per-deal severity scoring.** Rather than producing 20 proposals of equal weight, the system should score each deal on conversion-risk signals (false-discount math, empty fine print, missing trust signals) and surface the top 3 deals that most need attention. The current pipeline buries the 3 most urgent issues in a flat list of 20.
- **Shared city-level research.** Manhattan competitor pricing is the same query for every NYC salon deal. Caching research findings by `(city, category)` and reusing them across deals would cut Tavily calls ~40% and let the model reason across a portfolio.
- **Schema-validation guardrails on scrape.** If a future Groupon redesign breaks JSON-LD extraction, the parser should fail loudly, not silently return `None`. Add per-field assertions and a smoke-test deal that runs in CI.

## What surprised me

How often the deal pages contradict themselves — and how invisible those issues are without structured extraction:

- **asad-auto-repairs** claims "Up to 30% Off" in the title, but both SKUs are priced exactly 10% off. An existing 3-star reviewer is already alleging false advertising over a missing inspection. A real refund/chargeback risk, live in production.
- **gl-warner-bros-studio-tour-hollywood** carries a "limited time" urgency badge on tickets where `original_price == deal_price` across all four tiers — there is no discount.
- **balayage-me-salon-gramercy** claims "Up to 74% Off" but displays only ~10% off the listed anchors. The Pulsd voucher for an equivalent service is $89; this deal sits at $104.

These three are not outliers. A SQL query against the audit table shows 19 of 20 deals in this sample have the same title-vs-displayed-discount mismatch — auto repair, hair color, massage, salon, and ticketed-attraction categories are all affected. The pattern looks like merchant- or template-set "anchor" prices that no longer match the rendered price tiers, multiplied across thousands of live deals.

Cross-platform parity is also weaker than expected: scraping each deal once on desktop and once with a mobile UA showed 7 of 20 deals with material differences — most strikingly **main-massage-spa**, where the mobile render carries a "selling fast" urgency badge that the desktop render does not. Whether that's intentional A/B testing or template drift, the same shopper checking the page from two devices sees two different urgency stories.

These integrity issues are the single highest-leverage thing the system caught. They're page-by-page invisible to a human reviewer at scale, but trivially flagged once pricing structure lands in a column and you compare it to the H1. Most "optimization" advice talks about copy and imagery; the actual money on these 20 deals is in fixing what's already broken.
