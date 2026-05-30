# Implementation Plan — Groupon Deal Analyzer (v2)

> Pivot: from a **batch, developer-facing 20-deal report generator** → a **single-deal,
> consumer-facing "is this deal worth buying?" verdict tool**.
> Scope: **demo MVP**. Deploy: **Vercel (web) + Render (api, worker, Postgres)**.
> **All user-facing analysis output is in English.**

---

## 0. What changes vs the current repo

**Drop**
- DuckDB ([src/storage.py](src/storage.py)) — replaced by Postgres, owned by Go.
- Batch CLI ([src/cli.py](src/cli.py), `run --urls`, `refresh-audits`), `deals.txt`.
- `output/<slug>/` file dumping ([src/render.py](src/render.py)).
- Mobile-vs-desktop compare, the long `OptimizationProposal` ([src/synthesize.py](src/synthesize.py)).

**Keep / adapt**
- [src/scrape.py](src/scrape.py) — Playwright fetch (desktop only). Almost as-is.
- [src/parse.py](src/parse.py) + [src/parse_helpers.py](src/parse_helpers.py) — JSON-LD audit + per-tier `discount_pct`. The core value lives here.
- LLM structured-output pattern (`client.messages.parse` + Pydantic) from [src/research.py](src/research.py).

**New**
- Parse advertised discount from title (`"Up to 30% Off"`) → compare to actual max → `discount_verdict`.
- Competitor scrape (Groupon, same city).
- Cross-platform reputation compare (Groupon rating vs Yelp/Google).
- Direct-booking / official-site price check.
- Sonnet-generated **English** verdict (badges + one-liner).
- Go (Gin) API, Postgres cache, FastAPI worker wrapper, Vue frontend.

---

## 1. Architecture (locked)

```
Vue (Vercel)
  │  POST /analyze { url }
  ▼
Go / Gin (Render)            ← only stateful layer
  • check Postgres by url
  • cache hit & not expired → return cached result_json
  • miss → call Python worker → store → return
  ▼
Python worker / FastAPI (Render, Docker w/ Playwright)   ← stateless
  scrape → parse → Tavily(competitors + reviews) → Claude Sonnet → DealAnalysis JSON
  ▼
Postgres (Render)
  analyses(url PK, result_json JSONB, analyzed_at, expires_at)
```

---

## 2. Repo structure (monorepo)

```
/web        Vue 3 + Vite        → Vercel
/api        Go + Gin            → Render (web service)
/worker     Python + FastAPI    → Render (Docker, Playwright base image)
  /worker/analyzer/
     scrape.py        (adapted from src/scrape.py)
     parse.py         (adapted from src/parse.py)
     parse_helpers.py (adapted)
     discount.py      NEW — advertised vs actual
     competitors.py   NEW — Tavily-discover + Playwright-scrape Groupon local pages
     reputation.py    NEW — Tavily Yelp/Google + Sonnet gap summary
     direct.py        NEW — official-site / Yelp booking price check
     verdict.py       NEW — Sonnet → badges + one-liner (English)
     models.py        NEW — Pydantic DealAnalysis (the contract)
     pipeline.py      orchestrator → DealAnalysis
  /worker/main.py     FastAPI: POST /analyze { url } → DealAnalysis
PLAN.md
```
(Existing `src/` is copied into `/worker/analyzer` and trimmed; old root files removed once ported.)

---

## 3. Data contract — `DealAnalysis` (Python → Go → Vue)

The single most important artifact; all three layers depend on it. **All free-text fields in English.**

```jsonc
{
  "deal": {
    "url": "...",
    "title": "Quality Oil Change - Up to 30% Off",
    "merchant": "Asad Auto Repairs",
    "city": "Chicago",
    "category": "Oil Change",
    "advertised_discount_pct": 30,        // parsed from title "Up to X% Off" (null if none)
    "actual_max_discount_pct": 10,        // max over price tiers
    "discount_verdict": "exaggerated",    // honest | exaggerated | none
    "prices": [{ "label": "...", "original": 81, "deal": 72.9, "discount_pct": 10 }]
  },
  "reputation": {
    "groupon_rating": 3.5, "groupon_reviews": 4,
    "external_rating": 5.0, "external_reviews": 8, "external_source": "Yelp",
    "gap_verdict": "external_higher",     // external_higher | external_lower | consistent | insufficient
    "summary": "Yelp shows 5.0★ across 8 reviews vs only 3.5★ on Groupon; the on-platform sample is too small to be representative."
  },
  "competitors": [                         // same city, on Groupon
    { "merchant": "...", "title": "...", "price": 59, "discount_pct": 50,
      "url": "https://www.groupon.com/...", "cheaper": true }
  ],
  "direct_booking": {
    "cheaper_than_groupon": true,
    "note": "Bookable directly via Yelp; merchant site lists no online price.",
    "source_url": "..."
  },
  "verdict": {
    "badges": [
      { "type": "price",      "status": "ok",   "label": "Price is fair" },
      { "type": "discount",   "status": "bad",  "label": "Discount is exaggerated" },
      { "type": "reputation", "status": "warn", "label": "Big rating gap across platforms" }
    ],
    "worth_buying": "caution",            // yes | caution | no
    "one_liner": "Price is OK but the advertised discount is misleading — consider booking directly via Yelp.",
    "recommended_action": "..."
  },
  "meta": { "analyzed_at": "ISO8601", "cache_expires_at": "ISO8601" }
}
```

Pydantic models in `worker/analyzer/models.py` mirror this 1:1. Go unmarshals into a matching struct (or passes the JSONB through untouched — see §5).

---

## 4. Postgres schema (owned by Go)

```sql
CREATE TABLE analyses (
    url           TEXT PRIMARY KEY,
    result_json   JSONB NOT NULL,
    analyzed_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at    TIMESTAMPTZ NOT NULL          -- analyzed_at + TTL (24h MVP)
);
CREATE INDEX ON analyses (expires_at);
```
Cache key = the **normalized** Groupon URL (strip `?redemptionLocationId=...` and trailing slash — reuse the slug logic from `scrape.slug_from_url`, but key on full normalized URL so different deals stay distinct).

---

## 5. Go (Gin) API

- `POST /analyze` body `{ "url": "..." }`
  1. Normalize URL.
  2. `SELECT result_json FROM analyses WHERE url=$1 AND expires_at > now()` → hit returns immediately.
  3. Miss → `POST {WORKER_URL}/analyze` → on success `INSERT ... ON CONFLICT (url) DO UPDATE` → return.
  4. Worker error → 502 with a clean message.
- `GET /healthz`.
- CORS allowlist for the Vercel domain.
- For MVP, Go can treat `result_json` as opaque `json.RawMessage` (no need to mirror the full struct) — fewer places to keep in sync.
- Synchronous (no queue) for MVP; a single request may take 20–40s — frontend shows a spinner.

Env: `DATABASE_URL`, `WORKER_URL`, `ALLOWED_ORIGIN`.

---

## 6. Python worker pipeline (`worker/analyzer/pipeline.py`)

`analyze(url) -> DealAnalysis`:

1. **scrape** — Playwright desktop fetch (adapted `scrape.py`). MVP: in-process cache off; rely on Go's Postgres cache.
2. **parse** — `parse_audit()` → title, merchant, city, category, prices(+discount_pct), groupon rating/reviews.
3. **discount.py** — regex `Up to (\d+)% Off` from title → `advertised_discount_pct`; `actual_max_discount_pct = max(prices.discount_pct)`; verdict: `none` if actual≈0, `exaggerated` if advertised − actual ≥ ~10pp, else `honest`.
4. **competitors.py** — Tavily query `groupon {category} {city}` → keep results whose host is `groupon.com/local/...` → Playwright-scrape those category pages → extract deal cards (merchant, price, discount) → filter same city → mark `cheaper`.
5. **reputation.py** — Tavily `{merchant} {city} Yelp` / `Google reviews` → Sonnet extracts `external_rating/reviews/source` and writes the English `gap_verdict` + `summary`.
6. **direct.py** — Tavily `{merchant} {city} official site booking price` → Sonnet judges if direct/official is cheaper; English `note`.
7. **verdict.py** — Sonnet (`messages.parse`, Pydantic `Verdict`) given the assembled signals → `badges`, `worth_buying`, English `one_liner`, `recommended_action`. System prompt cached (`cache_control: ephemeral`).

Models: **Sonnet 4.6** everywhere (drop Opus — latency/cost for a live tool). Env: `ANTHROPIC_API_KEY`, `TAVILY_API_KEY`.

---

## 7. Vue frontend (`/web`)

Single page:
- URL input + "Analyze" button → `POST {VITE_API_URL}/analyze`.
- Loading state (spinner + "Scraping the live page, ~30s").
- Result view, top-to-bottom:
  1. **Verdict banner** — `worth_buying` color + `one_liner` + badge chips (green/yellow/red by `status`).
  2. **Discount truth** — advertised vs actual bar (`30%` claimed vs `10%` real).
  3. **Reputation gap** — Groupon ★ vs external ★ side by side + `summary`.
  4. **Cheaper alternatives** — competitor cards + direct-booking note.
- Env: `VITE_API_URL`.

---

## 8. Deployment

- **Vercel** — `/web` static build. Env `VITE_API_URL` → Render Go URL.
- **Render**
  - Go API: web service (Go buildpack). Env `DATABASE_URL`, `WORKER_URL`, `ALLOWED_ORIGIN`.
  - Python worker: **Docker** service from `mcr.microsoft.com/playwright/python` base (Chromium preinstalled). Env `ANTHROPIC_API_KEY`, `TAVILY_API_KEY`.
  - Managed Postgres.
  - Go → worker over Render internal URL.

---

## 9. Risks & MVP cutlines

- **Groupon bot detection from a datacenter IP (Render).** Biggest unknown — scraping that works locally may get blocked on Render. MVP mitigations: aggressive Postgres cache, realistic UA + stealth scrolls (already in `scrape.py`), accept occasional failure with a clean error. If it hard-blocks → add a residential proxy (out of MVP scope, note it).
- **Playwright memory/cold-start on Render.** Needs a paid instance; free tier may OOM. Accept slow cold starts for demo.
- **Synchronous 20–40s request.** No queue in MVP; spinner only. Fine for demo, revisit with async + polling for production.
- **External-rating extraction is noisy** (parsing Yelp stars from Tavily snippets). LLM-extracted, may be approximate — surface `insufficient` when unsure rather than guessing.
- **Tavily free 1000/mo.** Cache by URL covers repeat deals; competitor searches are the heaviest — consider reusing by `(city, category)` later.

---

## 10. Build order (milestones)

1. **Worker core, runnable as a CLI** — adapt `scrape`/`parse`, add `discount.py` + `models.py`; `python -m analyzer <url>` prints `DealAnalysis` with deal+discount filled. Fast iteration, no infra.
2. **Add competitors + reputation + direct + verdict** — full English `DealAnalysis` from a URL.
3. **Wrap in FastAPI** (`POST /analyze`).
4. **Go API + Postgres cache.**
5. **Vue frontend** against the live API.
6. **Deploy** (Vercel + Render).

Each milestone is independently runnable/demoable.
