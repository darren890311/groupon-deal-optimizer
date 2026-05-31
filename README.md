# Is This Groupon Deal Worth It?

A consumer tool that tells you whether a Groupon deal is actually a good buy. Paste a
deal link and it scrapes the live page, checks the **real** discount against the
advertised one, compares prices to similar same-city deals on Groupon, cross-references
the merchant's rating on Yelp/Google, and returns a clear **buy / caution / skip**
verdict — every claim grounded in scraped data, not vibes.

**▶︎ Live: https://groupon-analyzer-31548.web.app**

![screenshot](docs/screenshot.png)

---

## Why it exists

Groupon deal pages routinely advertise a headline discount ("Up to 50% Off") that's
larger than what the price tiers actually show, hide cheaper equivalents a few clicks
away, and lean on a thin on-platform review count. This tool does the legwork a careful
shopper can't do at scale and gives a straight answer.

## What it checks

| Signal | What it does |
| --- | --- |
| **Discount truth** | Parses the advertised claim from the title and compares it to the real strike-through discount on each price tier. Flags `genuine` / `exaggerated` / `none`. |
| **Like-for-like price** | Finds same-city deals on Groupon and uses an LLM to judge which are the *same* service vs merely *similar*, so a full-synthetic oil change isn't compared to a conventional one. |
| **Cross-platform reputation** | Pulls the merchant's Yelp/Google rating and compares it to the Groupon score — surfacing when a deal looks great on Groupon but rates lower elsewhere. |
| **Direct booking** | Checks whether booking the merchant directly (or via their site) beats the Groupon price. |
| **Verdict** | Combines the above into deterministic badges + an LLM-written one-liner and recommended action. |

## Architecture

```
Browser
   │  POST /analyze { url }
   ▼
Vue 3 (Firebase Hosting)
   ▼
Go / Gin gateway  ──────────►  Neon Postgres
   │  (cache by URL, 24h TTL)     (cache + history)
   │  identity-token auth
   ▼
Python worker (FastAPI, private)
   scrape (Playwright) → parse (BeautifulSoup + Groupon's embedded JSON)
   → discount math → similar-deal scrape → reputation/direct (Tavily + Claude)
   → verdict (Claude)
```

- **Stateless Python worker** does the heavy work (headless-Chromium scraping, LLM
  calls). It's deployed **private** on Cloud Run — only the Go gateway can reach it,
  via a Google-signed identity token — so the expensive backend can't be hit directly.
- **Go gateway** is the only stateful layer: it owns caching/history in Postgres and is
  the public entry point. The right-sized tool per layer — Go for the low-latency edge,
  Python for the scraping/ML.
- The three independent research stages (competitors, reputation, direct booking) run
  **concurrently**; only the final verdict waits on all of them.

## Tech stack

- **Frontend:** Vue 3 + Vite, deployed on **Firebase Hosting**
- **API gateway:** **Go** (Gin, pgx), packaged with a multi-stage Dockerfile, on **Cloud Run**
- **Worker:** **Python** (FastAPI, Playwright, BeautifulSoup), Dockerized, on **Cloud Run** (private)
- **Data:** **Neon** (serverless Postgres) for the analysis cache
- **AI/search:** **Claude** (Anthropic) for judgment + structured output, **Tavily** for web search
- **Infra:** GCP (Cloud Run, Cloud Build, Artifact Registry, IAM), Docker, service-to-service auth

## Engineering notes

A few decisions worth calling out:

- **Pricing is read from Groupon's embedded page data (`__NEXT_DATA__`), not JSON-LD.**
  On promo-code deals the JSON-LD reports the deal price as the anchor and the promo
  price as the "sale," yielding a wrong discount (e.g. 25% instead of the real 50%).
  Groupon's embedded `DealOption` data carries the true strike-through, which is what
  the page renders.
- **The worker is private.** `allUsers` invoke access is removed; the Go gateway
  authenticates with an OIDC identity token (`google.golang.org/api/idtoken`).
- **Failures aren't cached.** A datacenter IP occasionally gets a bot-challenge page;
  the worker retries once and, if still empty, returns an error instead of caching a
  bogus "no data" result for 24h.
- **The Go gateway is small on purpose** — a thin, tested edge (cache check → worker →
  store) with graceful shutdown, structured logging, context timeouts, and table-driven
  handler tests.

## Local development

Prereqs: Docker, Go 1.26+, Python 3.13+, Node 22+. Copy `.env.example` to `.env` and
fill in `ANTHROPIC_API_KEY` and `TAVILY_API_KEY`.

```bash
# 1. Postgres
docker compose up -d

# 2. Python worker  →  http://127.0.0.1:8000
cd worker && pip install -r requirements.txt && playwright install chromium
python -m uvicorn main:app --port 8000

# 3. Go gateway     →  http://127.0.0.1:8080
cd api && DATABASE_URL="postgres://postgres:postgres@127.0.0.1:5432/groupon" \
          WORKER_URL="http://127.0.0.1:8000" go run .

# 4. Frontend       →  http://127.0.0.1:5173
cd web && npm install && npm run dev
```

Quick CLI (no servers, analyzes one URL):

```bash
cd worker && python -m analyzer "https://www.groupon.com/deals/<slug>"
```

## Deployment

- **Worker & gateway** → Cloud Run via `gcloud run deploy --source` (Cloud Build builds
  the Dockerfiles). The worker is deployed with `--no-allow-unauthenticated`.
- **Frontend** → `firebase deploy --only hosting` (build with `VITE_API_URL` set to the
  gateway URL).
- **DB** → Neon free tier; connection string set as the gateway's `DATABASE_URL`.

## Repo layout

```
web/      Vue 3 frontend
api/      Go (Gin) gateway — internal/{config,store,server,worker}
worker/   Python FastAPI worker — analyzer/{scrape,parse,discount,competitors,reputation,direct,verdict}
docs/     screenshot
```
