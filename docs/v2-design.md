# Revelio v2 - Chrome Extension

## Why

The v1 website needs the user to copy a Groupon deal URL and paste it in - high
friction, low intent capture. v2 meets the shopper *where they already are*: a
Chrome extension that detects when they're on a Groupon deal page and offers to
"Reveal" whether it's worth buying (the Simplify pattern). The verdict shows in a
side panel; closing it leaves a logo tab (brand impression, zero cost).

This is **a new entry point, not a rewrite** - the Go gateway, Python worker,
Redis cache, Claude/Yelp/Google integrations are all reused.

## Spike result (validated 2026-06)

Confirmed in the browser console on a live deal page that everything v2 needs is
readable client-side:

- **Main deal pricing** lives in
  `JSON.parse(document.getElementById('__NEXT_DATA__').textContent).props.pageProps.__APOLLO_STATE__`
  (~184 KB, contains `option` + `strikethrough`/`regularPrice`). This is the *same*
  Apollo state the Python parser already reads - so the anti-promo-confusion
  parsing logic ports over unchanged; only the *input source* changes.
- **Competitors** are fully present in the rendered DOM's *Similar deals* cards:
  merchant, title, location, distance, **star rating + count**, original/sale/promo
  price, discount %. A content script reads them directly.

→ A content script can supply both. **Server-side Playwright is no longer needed
on the critical path.**

## Architecture

```
┌─ user's browser ──────────────────────────────────────────────┐
│  groupon.com/deals/*                                           │
│   content script:                                              │
│     • detect deal page → "Reveal?" prompt (no cost until click)│
│     • Phase 2: read __APOLLO_STATE__ + Similar-deals cards     │
│     • render panel (shadow DOM)                                │
│   service worker: fetch the API (host perms, not page CSP)     │
└──────────────┬─────────────────────────────────────────────────┘
               ▼  POST /analyze
        Go gateway → Redis cache (kept; hit-rate rises as many
               │ miss   users hit the same popular deal)
               ▼
        Python worker
          parse (reads Apollo state) · discount math ·
          LLM comparability · Google Places + Yelp · LLM verdict
               │
               ▼  verdict JSON → panel + CTA (affiliate deep-link)
```

## Phasing

- **Phase 1 (done):** extension sends `{ url }` to the existing `/analyze`; backend
  untouched. Working, ship-able, zero backend risk. See `extension/`.
- **Phase 2:** content script reads `__APOLLO_STATE__` + Similar-deals cards and
  POSTs that; worker accepts pre-parsed data and drops the Playwright fetch.

## Fate of each dependency in v2

| Tech | v2 | Reason |
| --- | --- | --- |
| Vue 3 | kept | panel UI moves into the content script |
| Go + Gin | kept | gateway, cache, future affiliate redirect |
| Redis | kept (more valuable) | many users hit the same popular deal → cache hit-rate rises |
| Python + FastAPI | kept | shrinks from "scrape + compute" to pure compute/judgment |
| Claude | kept | competitor comparability + verdict |
| Google Places + Yelp | kept | cross-platform ratings (not on the page) |
| **Tavily** | kept, narrowed | now only the **direct-booking** check (merchant's own-site price - genuinely off-Groupon, needs web search) |
| **Playwright** | off the fast path, kept as **fallback** | gone when the page is fresh (extension sends HTML); still used for the website's URL-only path and as the safety net when the extension page is stale (see SPA note below) |

## Decisions worth remembering

- **Competitors use the on-page *Similar deals*, not a Playwright deep search.**
  The LLM comparability step (same / similar / different) was always the real
  filter - the candidate *source* is interchangeable, so Groupon's "loose"
  recommendation list is fine input. Exhaustive deep search is only a future
  *nice-to-have* for price-percentile stats.
- **Analyze on click, never on page load.** Auto-running on every deal view would
  blow up LLM/API cost; the prompt is free, the analysis is opt-in.
- **No Groupon affiliate - Revelio stays a neutral advisor.** We explored the
  Groupon (CJ) affiliate program but decided against it: its terms forbid
  disparaging Groupon, making your own advertising claims, statistical analysis
  of Groupon content, and diverting customers - all core to what Revelio does
  (it says "not worth it", analyzes deals, and recommends booking direct). An
  honest watchdog can't be funded by the thing it critiques, and the commission
  is tiny (1%). So the buy CTA was removed from both the extension panel and the
  web app - Revelio gives the verdict; the user buys (or not) on the page itself.
  Future monetization, if any, should stay aligned: freemium (Pro features) or
  affiliate-linking the *recommended alternatives* (Klook / GetYourGuide /
  merchant), never Groupon.

## Stack note: vanilla JS → WXT + Vue

The first cut of the extension was a single vanilla-JS content script (zero build,
load-unpacked directly) - the right call for a tiny injected widget. As the panel
grew (prompt / loading / verdict + four sections / error), it was rebuilt with
**WXT + Vue 3**: the panel is Vue components mounted in a shadow root, TypeScript
entrypoints, auto-generated manifest. This matches how non-trivial extensions are
built (framework + bundler), gives Vue a second home alongside the web app, and - 
because there's now a bundler transpiling everything - TypeScript is "free" (it
needed a build step the vanilla version deliberately avoided).

## Issues found in testing & how they were fixed

Real deals surfaced bugs the happy path never hit. Each fix below shipped.

### 1. SPA staleness - sending the wrong deal's data (the big one)

Groupon is a single-page app. Navigating deal→deal (or search→deal) updates the
*visible DOM* but leaves the server-rendered `__NEXT_DATA__` blob on the
**first-loaded** deal - the URL and the on-screen content change, but the server
is never asked to re-render. The extension was sending `outerHTML`, so the worker
read the **stale** `__NEXT_DATA__`: a facial deal showed *New York CityPASS®
$164 → $164*, which then read as "53% claimed, 0% real → discount exaggerated."

**Fix:** the content script only sends the page when the `getDeal(...)` slug
embedded in `__NEXT_DATA__` matches the URL slug. On a mismatch (stale SPA nav)
it sends URL-only and the worker fetches the deal fresh with Playwright. Hence
Playwright's final role: not on the fast path, but the correctness fallback when
the page can't be trusted. (Future: an injected page-context script could read
the *live* `window.__APOLLO_CLIENT__` cache to stay fast even on SPA nav.)

### 2. Cross-scope comparisons - brand match ≠ same product

The comparability and direct-booking LLM steps matched on brand/name and ignored
*scope*:

- **Competitors:** a 5-attraction **New York CityPASS** ($164) was labelled
  `same` as a 3-attraction **CityPASS C3** and flagged "$114 cheaper."
- **Direct booking:** for the same 5-attraction pass it told the shopper to book
  the official **C3 ($109)** instead - a smaller package - as if cheaper.

**Fix:** an explicit rule in both prompts - a different quantity / count /
coverage / scope (attractions, sessions, days, area, items) is at most `similar`,
never `same`, **even when the brand name matches**; compare what's actually
included, not the label. Direct booking only counts a *same-scope* price as
cheaper, else reports it as not directly comparable.

### 3. Rating-gap verdict - "external higher" auto-passed a bad deal

A bus tour rated **2.8★ on Groupon (929 reviews)** but **4.4/4.6 on
Google/Yelp** scored "worth buying," because any `external_higher` gap was
treated as good - contradicting the consistency rule. A full-star gap backed by
a large Groupon sample is a real signal the Groupon experience differs.

**Fix:** a `divergent` gap verdict - `|diff| >= 1.0` with Groupon reviews `>= 100`
→ reputation badge `warn` → overall `caution`. A large gap on a *tiny* Groupon
sample stays `external_higher` (noise); `external_lower` stays a red flag.

### Takeaway

The recurring theme across 2 and 3: **the system must refuse to compare across
scopes / trust a single noisy signal.** Brand parity, a cheaper variant, or a
higher external score are not, by themselves, like-for-like - the judgment has to
check that the things being compared are actually the same.
