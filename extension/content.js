// Revelio extension — content script.
//
// Injects a small panel on Groupon deal pages. It starts as a "Reveal?" prompt
// (no analysis runs, so no cost), and only calls the API when the user opts in.
// All UI lives in a shadow root so Groupon's CSS can't leak in or out.

(() => {
  "use strict";

  const HOST_ID = "revelio-host";
  const LOGO = chrome.runtime.getURL("icon.png");

  // Per-deal UI state. Re-armed on SPA navigation (Groupon is a PWA).
  let collapsed = false; // user clicked X → show only the logo tab
  let lastHref = location.href;

  const isDealPage = () => location.pathname.startsWith("/deals/");

  // Centralized so swapping the raw deal URL for a Groupon affiliate deep link
  // later is a one-line change (mirrors web/src/api.js bookingUrl).
  function bookingUrl(dealUrl) {
    // TODO: wrap with the affiliate deep-link / params once enrolled.
    return dealUrl;
  }

  // ---- shadow host -------------------------------------------------------

  function shadow() {
    let host = document.getElementById(HOST_ID);
    if (!host) {
      host = document.createElement("div");
      host.id = HOST_ID;
      document.body.appendChild(host);
      const root = host.attachShadow({ mode: "open" });
      const style = document.createElement("style");
      style.textContent = STYLES;
      root.appendChild(style);
      const wrap = document.createElement("div");
      wrap.className = "wrap";
      root.appendChild(wrap);
    }
    return host.shadowRoot.querySelector(".wrap");
  }

  function teardown() {
    document.getElementById(HOST_ID)?.remove();
  }

  // ---- states ------------------------------------------------------------

  function renderCollapsed() {
    shadow().innerHTML = `
      <button class="tab" title="Open Revelio">
        <img src="${LOGO}" alt="Revelio" />
      </button>`;
    shadow().querySelector(".tab").onclick = () => {
      collapsed = false;
      renderPrompt();
    };
  }

  function renderPrompt() {
    const w = shadow();
    w.innerHTML = `
      <div class="card">
        ${header("Is this deal worth it?")}
        <p class="lede">Revelio checks the <b>real</b> discount, compares same-city prices, and cross-references Yelp/Google ratings.</p>
        <button class="cta reveal">✨ Reveal this deal</button>
      </div>`;
    wireHeader(w);
    w.querySelector(".reveal").onclick = reveal;
  }

  function renderLoading() {
    const w = shadow();
    w.innerHTML = `
      <div class="card">
        ${header("Revealing…")}
        <div class="loading">
          <img src="${LOGO}" class="spin" alt="" />
          <p class="lede">Reading the deal, finding similar ones, checking ratings — usually ~10s.</p>
        </div>
      </div>`;
    wireHeader(w);
  }

  function renderError(msg) {
    const w = shadow();
    w.innerHTML = `
      <div class="card">
        ${header("Couldn't reveal")}
        <p class="lede err">${escapeHtml(msg)}</p>
        <button class="cta reveal">Try again</button>
      </div>`;
    wireHeader(w);
    w.querySelector(".reveal").onclick = reveal;
  }

  function renderVerdict(data) {
    const w = shadow();
    const v = data.verdict || {};
    const deal = data.deal || {};
    const tone = TONE[v.worth_buying] || TONE.caution;

    const badges = (v.badges || [])
      .map((b) => `<span class="badge ${b.status}"><i></i>${escapeHtml(b.label)}</span>`)
      .join("");

    w.innerHTML = `
      <div class="card">
        ${header("Revelio")}
        <div class="verdict ${tone.cls}">
          <div class="vtag"><span class="vicon">${tone.icon}</span>${tone.label}</div>
          ${deal.title ? `<p class="dtitle">${escapeHtml(deal.title)}</p>` : ""}
          <p class="oneliner">${escapeHtml(v.one_liner || "")}</p>
          ${badges ? `<div class="badges">${badges}</div>` : ""}
          ${v.recommended_action ? `<p class="action"><b>What to do:</b> ${escapeHtml(v.recommended_action)}</p>` : ""}
          <a class="cta book" href="${bookingUrl(deal.url || location.href)}" target="_blank" rel="noopener">
            ${v.worth_buying === "yes" ? "Buy on Groupon →" : "Buy anyway on Groupon →"}
          </a>
        </div>
      </div>`;
    wireHeader(w);
  }

  // ---- shared header (close button) --------------------------------------

  function header(title) {
    return `
      <div class="hd">
        <span class="brand"><img src="${LOGO}" alt="" />${escapeHtml(title)}</span>
        <button class="x" title="Close">✕</button>
      </div>`;
  }

  function wireHeader(w) {
    const x = w.querySelector(".x");
    if (x) x.onclick = () => { collapsed = true; renderCollapsed(); };
  }

  // ---- analyze -----------------------------------------------------------

  function reveal() {
    renderLoading();
    const startedAt = Date.now();
    let settled = false;

    // Don't spin forever: an MV3 service worker can be recycled mid-request, in
    // which case the callback never fires. Surface a retryable error instead.
    const timer = setTimeout(() => {
      if (settled) return;
      settled = true;
      renderError("Timed out after 100s. The deal may be new (cold start) — try again.");
    }, 100000);

    chrome.runtime.sendMessage({ type: "ANALYZE", url: location.href }, (resp) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      console.debug(`[Revelio] analyze took ${((Date.now() - startedAt) / 1000).toFixed(1)}s`, resp);

      if (chrome.runtime.lastError) {
        renderError(chrome.runtime.lastError.message);
        return;
      }
      if (!resp) {
        renderError("No response from the extension background.");
        return;
      }
      if (!resp.ok) {
        renderError(resp.error || "Something went wrong.");
        return;
      }
      renderVerdict(resp.data);
    });
  }

  // ---- boot + SPA navigation re-arm --------------------------------------

  function boot() {
    if (!isDealPage()) {
      teardown();
      return;
    }
    collapsed ? renderCollapsed() : renderPrompt();
  }

  // ---- helpers -----------------------------------------------------------

  function escapeHtml(s) {
    return String(s ?? "").replace(/[&<>"']/g, (c) => (
      { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]
    ));
  }

  const TONE = {
    yes: { cls: "ok", label: "Worth buying", icon: "✓" },
    caution: { cls: "warn", label: "Buy with caution", icon: "⚠" },
    no: { cls: "bad", label: "Not worth it", icon: "✕" },
  };

  const STYLES = `
    :host { all: initial; }
    .wrap {
      position: fixed; top: 16px; right: 16px; z-index: 2147483647;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    .card {
      width: 340px; background: #1a1a1a; color: #f4f4f5;
      border: 1px solid #2e2e32; border-radius: 16px; padding: 16px 18px;
      box-shadow: 0 12px 40px rgba(0,0,0,.45);
    }
    .hd { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
    .brand { display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 15px; }
    .brand img { width: 20px; height: 20px; border-radius: 5px; }
    .x { background: transparent; border: 0; color: #9ca3af; font-size: 14px; cursor: pointer; padding: 4px; }
    .x:hover { color: #f4f4f5; }
    .lede { font-size: 13px; line-height: 1.5; color: #cbced4; margin: 0 0 14px; }
    .lede.err { color: #fca5a5; }
    .cta {
      display: block; width: 100%; text-align: center; box-sizing: border-box;
      padding: 10px 14px; border-radius: 10px; border: 0; cursor: pointer;
      font-weight: 650; font-size: 14px; text-decoration: none;
    }
    .reveal { background: #53a318; color: #fff; }
    .reveal:hover { background: #478c14; }
    .book { background: #53a318; color: #fff; margin-top: 14px; }
    .book:hover { background: #478c14; }
    .loading { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 6px 0 2px; }
    .spin { width: 44px; height: 44px; border-radius: 10px; animation: spin 1.4s linear infinite; }
    @keyframes spin { to { transform: rotateY(360deg); } }
    .loading .lede { text-align: center; margin: 0; }
    .tab {
      width: 46px; height: 46px; border-radius: 50%; border: 1px solid #2e2e32;
      background: #1a1a1a; cursor: pointer; box-shadow: 0 8px 24px rgba(0,0,0,.4);
      display: flex; align-items: center; justify-content: center;
    }
    .tab img { width: 26px; height: 26px; border-radius: 7px; }
    .verdict { border-radius: 12px; }
    .vtag { display: flex; align-items: center; gap: 9px; font-size: 18px; font-weight: 750; }
    .vicon {
      display: inline-flex; align-items: center; justify-content: center;
      width: 24px; height: 24px; border-radius: 50%; font-size: 13px; color: #fff; flex: none;
    }
    .verdict.ok .vtag { color: #4ade80; }  .verdict.ok .vicon { background: #16a34a; }
    .verdict.warn .vtag { color: #fbbf24; } .verdict.warn .vicon { background: #d97706; }
    .verdict.bad .vtag { color: #f87171; }  .verdict.bad .vicon { background: #dc2626; }
    .dtitle { font-size: 13px; font-weight: 600; margin: 10px 0 4px; color: #e5e7eb; }
    .oneliner { font-size: 13.5px; line-height: 1.5; margin: 8px 0 12px; }
    .badges { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 4px; }
    .badge {
      display: inline-flex; align-items: center; gap: 6px; font-size: 11.5px; font-weight: 600;
      padding: 4px 9px; border-radius: 999px; background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.12);
    }
    .badge i { width: 7px; height: 7px; border-radius: 50%; }
    .badge.ok i { background: #4ade80; } .badge.warn i { background: #fbbf24; } .badge.bad i { background: #f87171; }
    .action { font-size: 12.5px; line-height: 1.5; margin: 12px 0 0; color: #cbced4; }
  `;

  // ---- boot (after STYLES/TONE are initialized) --------------------------

  // Groupon is a single-page app, so a deal→deal navigation doesn't reload the
  // content script. Poll the URL and re-arm the prompt when it changes.
  setInterval(() => {
    if (location.href !== lastHref) {
      lastHref = location.href;
      collapsed = false;
      boot();
    }
  }, 1000);

  boot();
})();
