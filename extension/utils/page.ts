// Page helpers for the content script.

export const isDealPage = () => location.pathname.startsWith('/deals/');

// The current deal's slug from the URL path, e.g. /deals/<slug>?... → <slug>.
export function urlSlug(): string {
  return (location.pathname.split('/deals/')[1] || '').split(/[/?#]/)[0];
}

// Return the page HTML only if its server-rendered __NEXT_DATA__ describes the
// deal currently in the URL. On a Groupon SPA navigation that blob is stale (it
// still holds the first-loaded deal), so we return null and the worker fetches
// the correct deal fresh instead of mixing one deal's prices with another's.
export function pageHtmlIfFresh(): string | null {
  try {
    const nd = document.getElementById('__NEXT_DATA__');
    if (!nd?.textContent) return null;
    const root = JSON.parse(nd.textContent)?.props?.pageProps?.__APOLLO_STATE__?.ROOT_QUERY || {};
    const key = Object.keys(root).find((k) => k.startsWith('getDeal('));
    const m = key && key.match(/"id":"([^"]+)"/);
    const ndSlug = m && m[1];
    return ndSlug && ndSlug === urlSlug() ? document.documentElement.outerHTML : null;
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
