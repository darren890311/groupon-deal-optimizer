# Revelio Chrome Extension (WXT + Vue 3)

A Manifest V3 extension that surfaces Revelio's verdict **directly on the Groupon
deal page**. When you open a deal a small panel appears asking if you want to
*Reveal* it; the analysis (and its cost) only runs when you click.

Built with [WXT](https://wxt.dev) (the extension framework) and **Vue 3** — the
panel is Vue components rendered inside a Shadow DOM, so Groupon's CSS can't leak
in or out. It shares the same `/analyze` backend as the web app.

## Architecture

```
content script (Vue panel in a shadow root)
  │  detects a deal page → "Reveal?" prompt (no cost until click)
  │  on click: waits for on-page "Similar deals", sends the page (when fresh)
  ▼  chrome.runtime.sendMessage({ ANALYZE })
background service worker  ──POST /analyze {url, html?}──►  Go gateway → worker
  ▲                                                              │
  └──────────────── verdict JSON rendered in the panel ◄─────────┘
```

- The worker skips Playwright when the content script sends the rendered HTML.
  On a Groupon SPA navigation the embedded `__NEXT_DATA__` is stale, so the panel
  only sends the page when its `getDeal` slug matches the URL; otherwise it sends
  URL-only and the worker fetches the correct deal fresh.
- No buy CTA: Revelio is a neutral advisor (not a Groupon affiliate).

## Layout

| Path | Role |
| --- | --- |
| `wxt.config.ts` | manifest (name, permissions, host_permissions); icons/content-script/background are auto-derived |
| `entrypoints/background.ts` | service worker — makes the `/analyze` request |
| `entrypoints/content.ts` | content script — mounts the Vue panel in a shadow root |
| `components/Panel.vue` | state machine: prompt → loading → verdict / error, collapse-to-logo, SPA re-arm, styles |
| `components/Verdict.vue` | verdict + badges + the four collapsible detail sections |
| `components/Section.vue` | a collapsed `<details>` section with a takeaway pill |
| `utils/` | `page` (slug / freshness / wait-for-cards), `api` (analyze via background), `format` (money) |
| `public/icon/` | 16/48/128 toolbar icons · `assets/logo.png` panel logo |

## Develop & build

```bash
cd extension
npm install
npm run dev      # live-reloading dev build → .output/chrome-mv3-dev
npm run build    # production build       → .output/chrome-mv3
```

Then in `chrome://extensions` → enable **Developer mode** → **Load unpacked** →
pick `extension/.output/chrome-mv3` (or `…-dev`). Open any
`https://www.groupon.com/deals/...` page.

`API_BASE` in `entrypoints/background.ts` points at the live gateway; set it to
`http://127.0.0.1:8080` to test against a local one.
