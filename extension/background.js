// Revelio extension — background service worker.
//
// The network call lives here, not in the content script, on purpose: the
// service worker runs with the extension's own host permissions and isn't
// subject to Groupon's page Content-Security-Policy, so the fetch to our API
// can't be blocked by the page.

// Flip to "http://127.0.0.1:8080" to test against a local gateway.
const API_BASE = "https://groupon-api-xklyudhzbq-uc.a.run.app";

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg?.type !== "ANALYZE") return;
  analyze(msg.url, msg.html)
    .then((data) => sendResponse({ ok: true, data }))
    .catch((err) => sendResponse({ ok: false, error: err.message || "Request failed" }));
  return true; // keep the channel open for the async sendResponse
});

async function analyze(url, html) {
  const res = await fetch(`${API_BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(html ? { url, html } : { url }),
  });

  let data = null;
  try {
    data = await res.json();
  } catch {
    // non-JSON error body — fall through to the status-based message
  }

  if (!res.ok) {
    throw new Error(data?.error || data?.detail || `Request failed (${res.status})`);
  }
  return data;
}
