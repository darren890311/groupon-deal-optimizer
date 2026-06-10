# Revelio v2 — Chrome Extension

## Why

The v1 website needs the user to copy a Groupon deal URL and paste it in — high
friction, low intent capture. v2 meets the shopper *where they already are*: a
Chrome extension that detects when they're on a Groupon deal page and offers to
"Reveal" whether it's worth buying (the Simplify pattern). The verdict shows in a
side panel; closing it leaves a logo tab (brand impression, zero cost).

This is **a new entry point, not a rewrite** — the Go gateway, Python worker,
Redis cache, Claude/Yelp/Google integrations are all reused.

## Spike result (validated 2026-06)

Confirmed in the browser console on a live deal page that everything v2 needs is
readable client-side:

- **Main deal pricing** lives in
  `JSON.parse(document.getElementById('__NEXT_DATA__').textContent).props.pageProps.__APOLLO_STATE__`
  (~184 KB, contains `option` + `strikethrough`/`regularPrice`). This is the *same*
  Apollo state the Python parser already reads — so the anti-promo-confusion
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
| **Tavily** | kept, narrowed | now only the **direct-booking** check (merchant's own-site price — genuinely off-Groupon, needs web search) |
| **Playwright** | removable from critical path | both data sources move client-side; keep only as optional deep competitor search / fallback |

## Decisions worth remembering

- **Competitors use the on-page *Similar deals*, not a Playwright deep search.**
  The LLM comparability step (same / similar / different) was always the real
  filter — the candidate *source* is interchangeable, so Groupon's "loose"
  recommendation list is fine input. Exhaustive deep search is only a future
  *nice-to-have* for price-percentile stats.
- **Analyze on click, never on page load.** Auto-running on every deal view would
  blow up LLM/API cost; the prompt is free, the analysis is opt-in.
- **Affiliate = panel CTA via a deep-link** (method A: the user's last click goes
  through our link → attribution works, ToS-compliant). Never silently drop a
  cookie (cookie stuffing) and avoid intercepting Groupon's own buy button
  (the Honey-style last-click hijack). Affiliate application pending approval; the
  CTA currently links to the raw deal URL via a centralized `bookingUrl()` seam.
