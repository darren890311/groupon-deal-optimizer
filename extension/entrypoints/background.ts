// Background service worker. The network call lives here (not the content script)
// so it runs with the extension's host permissions and isn't blocked by Groupon's
// page Content-Security-Policy.

// Flip to "http://127.0.0.1:8080" to test against a local gateway.
const API_BASE = 'https://groupon-api-xklyudhzbq-uc.a.run.app';

export default defineBackground(() => {
  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg?.type !== 'ANALYZE') return;
    analyze(msg.url, msg.html)
      .then((data) => sendResponse({ ok: true, data }))
      .catch((err) => sendResponse({ ok: false, error: err?.message || 'Request failed' }));
    return true; // keep the channel open for the async sendResponse
  });
});

async function analyze(url: string, html?: string) {
  const res = await fetch(`${API_BASE}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(html ? { url, html } : { url }),
  });

  let data: any = null;
  try {
    data = await res.json();
  } catch {
    // non-JSON error body — fall through to the status-based message
  }

  if (!res.ok) throw new Error(data?.error || data?.detail || `Request failed (${res.status})`);
  return data;
}
