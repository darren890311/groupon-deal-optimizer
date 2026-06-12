// Page helpers for the content script.

export const isDealPage = () => location.pathname.startsWith('/deals/');

// The current deal's slug from the URL path, e.g. /deals/<slug>?... → <slug>.
export function urlSlug(): string {
  return (location.pathname.split('/deals/')[1] || '').split(/[/?#]/)[0];
}

// The deal id that a page's server-rendered __NEXT_DATA__ blob describes, or null.
// On a Groupon SPA navigation the *live* blob is stale (it still holds the
// first-loaded deal), which is how we tell a fresh page from a stale one.
function nextDataSlug(doc: Document): string | null {
  const nd = doc.getElementById('__NEXT_DATA__');
  if (!nd?.textContent) return null;
  try {
    const root = JSON.parse(nd.textContent)?.props?.pageProps?.__APOLLO_STATE__?.ROOT_QUERY || {};
    const key = Object.keys(root).find((k) => k.startsWith('getDeal('));
    const m = key && key.match(/"id":"([^"]+)"/);
    return (m && m[1]) || null;
  } catch {
    return null;
  }
}

// Live page HTML, but only if its __NEXT_DATA__ already describes the deal in the
// URL (direct load / refresh). The live DOM also carries the rendered "Similar
// deals" cards, so this is the richest source when it's fresh.
export function pageHtmlIfFresh(): string | null {
  return nextDataSlug(document) === urlSlug() ? document.documentElement.outerHTML : null;
}

// Fresh HTML for the *current* deal, so the worker can always skip Playwright.
//   1. If the live page is already fresh (direct load / refresh), use it.
//   2. Otherwise the user reached this deal by an SPA click from another page,
//      so __NEXT_DATA__ is stale. Re-fetch the deal URL same-origin (with the
//      user's session) to get the server-rendered HTML for THIS deal — the same
//      thing a manual refresh would load, but without reloading the page.
// Returns null only if we can't confirm a match, in which case the worker falls
// back to its own scrape.
export async function freshDealHtml(): Promise<string | null> {
  const live = pageHtmlIfFresh();
  if (live) return live;
  try {
    const res = await fetch(location.href, { credentials: 'include' });
    if (!res.ok) return null;
    const html = await res.text();
    const doc = new DOMParser().parseFromString(html, 'text/html');
    return nextDataSlug(doc) === urlSlug() ? html : null;
  } catch {
    return null;
  }
}

// Recommendations lazy-load after hydration; resolve once a card is in the DOM
// (or after a short cap, so a deal with genuinely no similar deals still runs).
export function waitForCards(timeout = 4000): Promise<void> {
  return new Promise((resolve) => {
    if (document.querySelector('a[data-bhd]')) return resolve();
    const t0 = Date.now();
    const iv = setInterval(() => {
      if (document.querySelector('a[data-bhd]') || Date.now() - t0 > timeout) {
        clearInterval(iv);
        resolve();
      }
    }, 200);
  });
}
