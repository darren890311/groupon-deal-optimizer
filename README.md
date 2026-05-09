# Groupon Deal Page Optimizer

Pipeline that takes Groupon deal URLs, scrapes them, runs competitive and merchant research, and produces an actionable optimization proposal per deal — backed by quoted evidence from reviews and competitor data.

## Outputs per deal (in `output/<slug>/`)

- `audit.json` / `audit.md` — every structured element of the live page (title, pricing, highlights, fine print, reviews, SEO, trust + urgency signals)
- `research.json` / `research.md` — competitive pricing, reputation, category benchmarks, content gaps (with sources)
- `proposal.json` / `proposal.md` — prioritized recommendations, each tied to specific scraped or researched evidence

All structured data also lives in `data/groupon.duckdb` (queryable via DuckDB CLI).

## Setup

```bash
pip install -r requirements.txt
playwright install chromium
cp .env.example .env  # fill in ANTHROPIC_API_KEY and TAVILY_API_KEY
```

## Run

```bash
# Process all URLs in deals.txt
python -m src run --urls deals.txt

# One-off
python -m src one "https://www.groupon.com/deals/<slug>"

# Resume — skips deals whose proposal.md already exists
python -m src run --urls deals.txt

# Force re-process
python -m src run --urls deals.txt --force
```

## Architecture

```
URL → scrape (Playwright, HTML cached to data/raw_html/<slug>.html)
    → parse  (BeautifulSoup + JSON-LD product schema → audit dict)
    → store  (DuckDB: deals, prices, reviews)
    → research (Claude generates Tavily queries → searches → extract themes)
    → store  (DuckDB: research_findings)
    → synthesize (Claude Opus 4.7, adaptive thinking, structured output via Pydantic)
    → store  (DuckDB: recommendations)
    → render (Markdown + JSON to output/<slug>/)
```

### AI integration

Claude is wired into the pipeline at three judgment points, not just as final summarization:

1. **`research.generate_queries`** — Claude (Sonnet 4.6) reads the audit and emits 5–7 Tavily queries spanning competitor pricing, reputation, category benchmarks, and content gaps. Structured output via Pydantic (`messages.parse()`).
2. **`research.extract_review_themes`** — Claude (Sonnet 4.6) extracts recurring positive/negative themes from research snippets, with verbatim quotes.
3. **`synthesize.synthesize_proposal`** — Claude (Opus 4.7, adaptive thinking, `effort: "high"`) writes the proposal grounded in audit + research data. The system prompt is ~5 KB of detailed rubric, marked with `cache_control: ephemeral` so the prefix is reused across all 20 deals (~90% input-cost reduction after the first call).

### Schema

```sql
deals(slug PK, url, title, merchant_name, city, region, category, rating, review_count, bought_label, ...)
prices(slug, option_idx, label, original_price, deal_price, discount_pct)
reviews(slug, review_idx, rating, quote, author, date)
research_findings(slug, finding_idx, category, query, source_url, snippet)
recommendations(slug, rec_idx, field, current_value, proposed_value, rationale, evidence, priority)
```

## Adding more deals

Append URLs to `deals.txt`, one per line. The CLI deduplicates by slug and skips deals that already have a `proposal.md`.

## Notes

- Groupon pages are JS-rendered with bot detection — the scraper uses Playwright (Chromium, realistic UA, lazy-load scrolls). Raw HTML is cached so re-runs of parse/research/synthesize don't re-scrape.
- Tavily free tier allows 1000 calls/month; 20 deals × ~5 queries = ~100 calls.
