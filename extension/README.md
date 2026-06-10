# Revelio Chrome Extension (v2)

A Manifest V3 extension that surfaces Revelio's verdict **directly on the Groupon
deal page** — no copy-pasting a URL into the website. When you open a deal page a
small panel appears asking if you want to *Reveal* it; the analysis (and its cost)
only runs when you click.

## Phase 1 (current)

The extension is a new **front end** for the existing API. It detects a deal page,
and on *Reveal* it sends `{ url }` to the same `/analyze` gateway the website uses.
The backend (Go gateway, Python worker, Playwright scraping, Redis cache) is
unchanged. This ships a working extension with zero backend risk.

```
content script  ──ANALYZE msg──►  service worker  ──POST /analyze {url}──►  gateway
   (deal page)                     (background.js)                           (existing)
       ▲                                                                        │
       └──────────────── verdict JSON rendered in the panel ◄───────────────────┘
```

Phase 2 (later): move scraping client-side — the content script reads the deal's
`__NEXT_DATA__.props.pageProps.__APOLLO_STATE__` and the on-page *Similar deals*
cards and POSTs that instead of a URL, so the worker drops server-side Playwright.
See [../docs/v2-design.md](../docs/v2-design.md).

## Files

| File | Role |
| --- | --- |
| `manifest.json` | MV3 config — runs only on `https://www.groupon.com/deals/*`, declares the API host. |
| `content.js` | Detects the deal page, injects the panel (shadow DOM), renders prompt → loading → verdict. |
| `background.js` | Service worker; makes the `/analyze` request (runs with extension host permissions, not the page CSP). |
| `icon.png` | Toolbar / panel logo. |

## Load it (unpacked, for testing)

1. Open `chrome://extensions`.
2. Toggle **Developer mode** (top right).
3. **Load unpacked** → pick this `extension/` folder.
4. Open any Groupon deal page (`https://www.groupon.com/deals/...`). The panel
   appears top-right. Click **Reveal**.

By default it calls the live API (`groupon-api-...run.app`). To test against a
local gateway, set `API_BASE` in `background.js` to `http://127.0.0.1:8080` and
reload the extension.

## Notes

- The panel's "Buy on Groupon" link currently points at the raw deal URL. The
  affiliate deep-link is a one-line change in `bookingUrl()` (in `content.js`)
  once the Groupon affiliate application is approved.
- All UI is rendered inside a shadow root, so Groupon's page styles can't bleed
  into the panel (or vice versa).
- Groupon is a single-page app; the content script polls the URL and re-arms the
  prompt when you navigate from one deal to another.
