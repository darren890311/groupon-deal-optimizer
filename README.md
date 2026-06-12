# Revelio - Is This Deal Actually A Deal?

Revelio tells you whether a Groupon deal is actually a good buy. It comes as a **Chrome
extension** that pops up on any Groupon deal page, and a **web app** where you paste a
deal link. Either way it reads the live page, checks the **real** discount against the
advertised one, compares prices to similar same-city deals, cross-references the
merchant's rating on Google/Yelp, and returns a clear **buy / caution / skip** verdict - 
every claim grounded in real data, not vibes.

Revelio is an **independent tool - not affiliated with or endorsed by Groupon.**

**▶︎ Live web app: https://getrevelio.web.app** · [Privacy policy](https://getrevelio.web.app/privacy.html)

---

## Why it exists

Groupon deal pages routinely advertise a headline discount ("Up to 50% Off") that's
larger than what the price tiers actually show, hide cheaper equivalents a few clicks
away, and lean on a thin on-platform review count. Revelio does the legwork a careful
shopper can't do at scale and gives a straight answer.

## What it checks

| Signal | What it does |
| --- | --- |
| **Discount truth** | Parses the advertised claim from the title and compares it to the real strike-through discount on each price tier. Flags `genuine` / `exaggerated` / `none`. |
| **Like-for-like price** | Finds same-city deals on Groupon and uses an LLM to judge which are the *same* service vs merely *similar* - refusing to compare across scope (a 3-attraction pass is not "the same" as a 5-attraction one, even under the same brand). |
| **Cross-platform reputation** | Pulls the merchant's structured rating from the **Google Places** and **Yelp Fusion** APIs and compares both to the Groupon score. A large, well-sampled gap is flagged as *ratings disagree*; multi-location chains are flagged as *varies by location* rather than guessed. |
| **Direct booking** | Checks whether booking the merchant directly (or via an official reseller) beats the Groupon price - comparing only same-scope prices, and staying silent when it's too close to call. |
| **Verdict** | Combines the above into deterministic badges + an LLM-written one-liner and recommended action. Revelio is neutral: it has no buy button and earns nothing on a purchase. |

## Architecture

Two front-ends, one backend:

```
┌─ Chrome extension (WXT + Vue 3) ─┐        ┌─ Web app (Vue 3) ────┐
│ reads the deal page in-browser,  │        │ paste a deal link    │
│ POST /analyze { url, html }      │        │ POST /analyze { url } │
└───────────────┬──────────────────┘        └──────────┬───────────┘
                ▼                                        ▼
            Go / Gin gateway  ──────────►  Upstash Redis  (cache by URL, 24h TTL)
                │  identity-token auth
                ▼
            Python worker (FastAPI, private, Cloud Run)
              parse (BeautifulSoup + Groupon's embedded __NEXT_DATA__ / __APOLLO_STATE__)
              → discount math → competitors (Claude) → reputation (Google Places + Yelp Fusion)
              → direct booking (Tavily + Claude) → verdict (Claude)
              ↑ headless-Chromium scrape (Playwright) ONLY when no page HTML was supplied
```

- **The extension reads the page client-side.** It sends the rendered HTML (and reads
  the on-page *Similar deals* for competitors), so the worker **skips Playwright
  entirely** - no cold-start, no bot-challenge, no datacenter-IP geography issue.
  Playwright remains the **web app's path and a fallback** for when the page can't be
  trusted (see notes).
- **Stateless Python worker** does the analysis (LLM calls, and scraping only on the
  fallback path). It's **private** on Cloud Run - only the Go gateway can reach it via a
  Google-signed identity token.
- **Go gateway** is the only stateful layer: it owns the Redis cache and is the public
  entry point. Right-sized tool per layer - Go for the low-latency edge, Python for ML.
- The three research stages (competitors, reputation, direct booking) run
  **concurrently**; only the final verdict waits on all of them.

## Tech stack

- **Front-ends:** **Vue 3** + Vite - a web app on **Firebase Hosting**, and a **Chrome
  MV3 extension** built with **WXT** (panel mounted in a Shadow DOM)
- **API gateway:** **Go** (Gin, go-redis), multi-stage Dockerfile, on **Cloud Run**
- **Worker:** **Python** (FastAPI, Playwright, BeautifulSoup), Dockerized, on **Cloud Run** (private)
- **Data:** **Upstash** (serverless Redis) for the analysis cache - URL key → result with a native TTL
- **AI/search:** **Claude** (Anthropic) for judgment + structured output, **Tavily** for web search
- **External APIs:** **Google Places** + **Yelp Fusion** for structured cross-platform ratings
- **Infra:** GCP (Cloud Run, Cloud Build, Artifact Registry, IAM), Docker, service-to-service auth

## Engineering notes

A few decisions worth calling out:

- **One backend, two clients - and the extension makes scraping client-side.** The
  extension reads the deal page in the user's own browser (real IP, page already
  rendered) and posts the HTML, so the worker doesn't run headless Chromium for it.
- **Stale `__NEXT_DATA__` on SPA navigation is detected.** Groupon is a single-page app:
  navigating deal→deal updates the DOM but leaves the server-rendered `__NEXT_DATA__` on
  the first deal. The extension only sends the page when its embedded `getDeal` slug
  matches the URL; otherwise it sends URL-only and the worker fetches the deal fresh.
- **Pricing is read from Groupon's embedded data (`__NEXT_DATA__`), not JSON-LD.** On
  promo-code deals the JSON-LD reports the deal price as the anchor and the promo price
  as the "sale," yielding a wrong discount; the embedded `DealOption` data carries the
  true strike-through.
- **Judgments refuse cross-scope comparisons.** Comparability and direct-booking treat a
  different quantity/coverage (3 vs 5 attractions, a smaller package) as at most
  *similar*, never *same*, even under a matching brand. A full-star, well-sampled
  rating gap downgrades the verdict to *caution*. Decisions (who's cheaper, worth-buying)
  are computed in code; the LLM only extracts and narrates.
- **The worker is private.** `allUsers` invoke access is removed; the gateway
  authenticates with an OIDC identity token (`google.golang.org/api/idtoken`).
- **Failures aren't cached.** A datacenter IP occasionally gets a bot-challenge page; the
  worker retries once and, if still empty, returns an error instead of caching "no data".
- **Yelp ratings come from the Fusion API, not web search** (Yelp renders stars as
  images), and no-city chains are anchored with `regionCode=US`.
- **No affiliate, by design.** Revelio gives the verdict and has no buy button - an
  honest advisor shouldn't be paid by the platform it critiques.

## Local development

Prereqs: Docker, Go 1.26+, Python 3.13+, Node 22+. Copy `.env.example` to `.env` and
fill in `ANTHROPIC_API_KEY`, `TAVILY_API_KEY`, `GOOGLE_PLACES_API_KEY`, and `YELP_API_KEY`
(each stage degrades gracefully if its key is missing).

```bash
# 1. Redis (local) - or point REDIS_URL at an Upstash instance instead
docker compose up -d

# 2. Python worker  →  http://127.0.0.1:8000
cd worker && pip install -r requirements.txt && playwright install chromium
python -m uvicorn main:app --port 8000

# 3. Go gateway     →  http://127.0.0.1:8080
cd api && REDIS_URL="redis://127.0.0.1:6379" \
          WORKER_URL="http://127.0.0.1:8000" go run .

# 4a. Web app       →  http://127.0.0.1:5173
cd web && npm install && npm run dev

# 4b. Extension     →  build, then load .output/chrome-mv3 unpacked
cd extension && npm install && npm run dev   # (set API_BASE in entrypoints/background.ts to localhost)
```

Quick CLI (no servers, analyzes one URL):

```bash
cd worker && python -m analyzer "https://www.groupon.com/deals/<slug>"
```

## Deployment

- **Worker & gateway** → Cloud Run via `gcloud run deploy --source` (GitHub Actions on
  push to `api/**` and `worker/**`). The worker is `--no-allow-unauthenticated`.
- **Web app** → Firebase Hosting (GitHub Actions on push to `web/**`).
- **Cache** → Upstash Redis free tier; connection string set as the gateway's `REDIS_URL`.
- **Extension** → `cd extension && npm run build` (or `npm run zip` to package for the
  Chrome Web Store); loaded/published manually, not via CI.

## Repo layout

```
web/         Vue 3 web app (+ public/privacy.html)
extension/   WXT + Vue 3 Chrome MV3 extension - entrypoints/, components/, utils/
api/         Go (Gin) gateway - internal/{config,store,server,worker}
worker/      Python FastAPI worker - analyzer/{scrape,parse,discount,competitors,reputation,direct,verdict}
docs/        v2 design notes + screenshot
```
