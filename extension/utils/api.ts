import { pageHtmlIfFresh, waitForCards } from './page';

// Run an analysis for the current deal: wait for the on-page Similar deals to
// render, send the page (when fresh) to the background worker, and resolve with
// the result. Rejects on error or a 100s timeout (an MV3 service worker can be
// recycled mid-request, leaving the callback to never fire).
export function analyze(): Promise<any> {
  return new Promise((resolve, reject) => {
    let settled = false;
    const startedAt = Date.now();

    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      reject(new Error('Timed out after 100s. The deal may be new (cold start) — try again.'));
    }, 100000);

    waitForCards().then(() => {
      const html = pageHtmlIfFresh();
      chrome.runtime.sendMessage(
        { type: 'ANALYZE', url: location.href, html: html || undefined },
        (resp) => {
          if (settled) return;
          settled = true;
          clearTimeout(timer);
          console.debug(`[Revelio] analyze took ${((Date.now() - startedAt) / 1000).toFixed(1)}s`, resp);

          if (chrome.runtime.lastError) return reject(new Error(chrome.runtime.lastError.message));
          if (!resp) return reject(new Error('No response from the extension background.'));
          if (!resp.ok) return reject(new Error(resp.error || 'Something went wrong.'));
          resolve(resp.data);
        },
      );
    });
  });
}
