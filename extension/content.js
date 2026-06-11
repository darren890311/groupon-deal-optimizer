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
        </div>

        <div class="sections">
          ${discountSection(deal)}
          ${reputationSection(data.reputation)}
          ${competitorsSection(data.competitors)}
          ${directSection(data.direct_booking)}
        </div>

        <a class="cta book" href="${bookingUrl(deal.url || location.href)}" target="_blank" rel="noopener">
          ${v.worth_buying === "yes" ? "Buy on Groupon →" : "Buy anyway on Groupon →"}
        </a>
      </div>`;
    wireHeader(w);
  }

  // ---- detail sections (collapsed; <summary> carries a one-line takeaway) --

  const DISCOUNT_VERDICT = {
    honest: { cls: "ok", word: "genuine" },
    exaggerated: { cls: "bad", word: "exaggerated" },
    none: { cls: "warn", word: "no real discount" },
  };

  function discountSection(deal) {
    if (!deal) return "";
    const dv = DISCOUNT_VERDICT[deal.discount_verdict] || { cls: "warn", word: deal.discount_verdict || "—" };
    const max = deal.actual_max_discount_pct != null ? `up to ${Math.round(deal.actual_max_discount_pct)}%` : "";
    const claim = deal.advertised_discount_pct != null
      ? `Headline claim: ${Math.round(deal.advertised_discount_pct)}% · `
      : "No headline % claim · ";
    const tiers = (deal.prices || []).map((p) => `
      <div class="row">
        <span class="rl">${escapeHtml(p.label || "Option")}</span>
        <span class="rr">${p.original != null ? `<s>${money(p.original)}</s> ` : ""}${money(p.deal)}${p.discount_pct != null ? ` <em>-${Math.round(p.discount_pct)}%</em>` : ""}</span>
      </div>`).join("");
    return section(
      `Discount`,
      `<span class="pill ${dv.cls}">${dv.word}</span> ${max}`,
      `<p class="note">${claim}real strike-through per option:</p>${tiers}`,
    );
  }

  const GAP = {
    consistent: { cls: "ok", text: "consistent" },
    external_higher: { cls: "ok", text: "external higher" },
    external_lower: { cls: "bad", text: "external lower" },
    divergent: { cls: "warn", text: "ratings disagree" },
    insufficient: { cls: "warn", text: "limited data" },
  };

  function reputationSection(rep) {
    if (!rep) return "";
    const g = GAP[rep.gap_verdict] || { cls: "warn", text: rep.gap_verdict || "—" };
    const star = (r, n) => r != null
      ? `<span class="star">${Number(r).toFixed(1)}★<small>${n != null ? ` (${Number(n).toLocaleString()})` : ""}</small></span>`
      : `<span class="star muted">—</span>`;
    const stats = `
      <div class="stars">
        <div><b>Groupon</b>${star(rep.groupon_rating, rep.groupon_reviews)}</div>
        <div><b>Google</b>${star(rep.google_rating, rep.google_reviews)}</div>
        <div><b>Yelp</b>${star(rep.yelp_rating, rep.yelp_reviews)}</div>
      </div>`;
    const cls = rep.chain ? "warn" : g.cls;
    const takeaway = rep.chain ? "varies by location" : g.text;
    return section(
      `Reputation`,
      `<span class="pill ${cls}">${takeaway}</span>`,
      `${stats}${rep.summary ? `<p class="note">${escapeHtml(rep.summary)}</p>` : ""}`,
    );
  }

  const MATCH = { same: "ok", similar: "warn", different: "muted" };

  function competitorsSection(comps) {
    if (!comps || !comps.length) {
      return section(`Competitors`, `<span class="pill muted">none found</span>`, `<p class="note">No comparable same-city deals found.</p>`);
    }
    const rows = comps.map((c) => `
      <div class="comp">
        <div class="comp-top">
          <a href="${escapeHtml(c.url || "#")}" target="_blank" rel="noopener">${escapeHtml(c.merchant || c.title || "—")}</a>
          <span class="rr">${money(c.price)}${c.cheaper ? ` <em class="bad">cheaper ↓</em>` : ""}</span>
        </div>
        <div class="comp-sub">
          <span class="pill ${MATCH[c.match] || "muted"}">${escapeHtml(c.match || "—")}</span>
          ${c.difference_note ? `<span class="diff">${escapeHtml(c.difference_note)}</span>` : ""}
        </div>
      </div>`).join("");
    const anyCheaper = comps.some((c) => c.cheaper);
    return section(
      `Competitors`,
      `<span class="pill ${anyCheaper ? "warn" : "ok"}">${comps.length} found${anyCheaper ? " · cheaper exists" : ""}</span>`,
      rows,
    );
  }

  function directSection(db) {
    if (!db) return "";
    // Three states: cheaper elsewhere (warn) / Groupon wins (ok) / unknown or
    // too-close-to-call (muted → "verify").
    const c = db.cheaper_than_groupon;
    const tag = c === true ? { cls: "warn", text: "may be cheaper" }
      : c === false ? { cls: "ok", text: "Groupon wins" }
      : { cls: "muted", text: "verify price" };
    return section(
      `Direct booking`,
      `<span class="pill ${tag.cls}">${tag.text}</span>`,
      `${db.note ? `<p class="note">${escapeHtml(db.note)}</p>` : ""}${db.source_url ? `<a class="src" href="${escapeHtml(db.source_url)}" target="_blank" rel="noopener">source ↗</a>` : ""}`,
    );
  }

  function section(title, takeaway, body) {
    return `
      <details>
        <summary><span class="st">${escapeHtml(title)}</span>${takeaway}<span class="chev">›</span></summary>
        <div class="sbody">${body}</div>
      </details>`;
  }

  function money(n) {
    if (n == null) return "—";
    return "$" + (Number.isInteger(n) ? n : Number(n).toFixed(2));
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

    // The on-page "Similar deals" cards (a[data-bhd]) are lazy-loaded; wait for
    // them so the rendered HTML we send carries the competitors too. Then send
    // the whole page so the worker can skip Playwright entirely.
    waitForCards().then(() => sendForAnalysis());

    function sendForAnalysis() {
      // Only send the page when its embedded __NEXT_DATA__ actually belongs to
      // THIS deal. On a Groupon SPA navigation (deal→deal, or from search) the
      // server-rendered __NEXT_DATA__ stays stale on the first-loaded deal even
      // though the visible DOM updates — sending it would mix one deal's prices
      // with another's. When stale, send only the URL and let the worker fetch
      // the correct deal fresh.
      const html = pageHtmlIfFresh();
      chrome.runtime.sendMessage({ type: "ANALYZE", url: location.href, html: html || undefined }, (resp) => {
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
  }

  // The current deal's slug from the URL path, e.g. /deals/<slug>?... → <slug>.
  function urlSlug() {
    return (location.pathname.split("/deals/")[1] || "").split(/[/?#]/)[0];
  }

  // Return the page HTML only if its server-rendered __NEXT_DATA__ describes the
  // deal currently in the URL. On a SPA navigation that blob is stale (it still
  // holds the first-loaded deal), so we return null and fall back to a URL-only
  // request, which the worker fetches fresh.
  function pageHtmlIfFresh() {
    try {
      const nd = document.getElementById("__NEXT_DATA__");
      if (!nd) return null;
      const root = JSON.parse(nd.textContent)?.props?.pageProps?.__APOLLO_STATE__?.ROOT_QUERY || {};
      const key = Object.keys(root).find((k) => k.startsWith("getDeal("));
      const m = key && key.match(/"id":"([^"]+)"/);
      const ndSlug = m && m[1];
      return ndSlug && ndSlug === urlSlug() ? document.documentElement.outerHTML : null;
    } catch {
      return null;
    }
  }

  // Recommendations lazy-load after hydration; resolve once a card is in the DOM
  // (or after a short cap, so a deal with genuinely no similar deals still runs).
  function waitForCards(timeout = 4000) {
    return new Promise((resolve) => {
      if (document.querySelector("a[data-bhd]")) return resolve();
      const t0 = Date.now();
      const iv = setInterval(() => {
        if (document.querySelector("a[data-bhd]") || Date.now() - t0 > timeout) {
          clearInterval(iv);
          resolve();
        }
      }, 200);
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
      max-height: calc(100vh - 32px); overflow-y: auto; overscroll-behavior: contain;
    }
    .card::-webkit-scrollbar { width: 8px; }
    .card::-webkit-scrollbar-thumb { background: #3a3a40; border-radius: 4px; }
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

    /* collapsible detail sections */
    .sections { margin: 14px 0 4px; border-top: 1px solid #2e2e32; }
    details { border-bottom: 1px solid #2e2e32; }
    summary {
      list-style: none; cursor: pointer; display: flex; align-items: center; gap: 8px;
      padding: 10px 2px; font-size: 12.5px;
    }
    summary::-webkit-details-marker { display: none; }
    .st { font-weight: 650; color: #f4f4f5; }
    .chev { margin-left: auto; color: #9ca3af; transition: transform .15s; }
    details[open] .chev { transform: rotate(90deg); }
    .sbody { padding: 2px 2px 12px; }
    .pill {
      font-size: 11px; font-weight: 650; padding: 2px 8px; border-radius: 999px;
      background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.12); white-space: nowrap;
    }
    .pill.ok { color: #4ade80; } .pill.warn { color: #fbbf24; } .pill.bad { color: #f87171; } .pill.muted { color: #9ca3af; }
    .note { font-size: 12px; line-height: 1.5; color: #cbced4; margin: 0 0 8px; }
    .row { display: flex; justify-content: space-between; gap: 10px; font-size: 12px; padding: 4px 0; border-top: 1px solid #242428; }
    .rl { color: #cbced4; flex: 1; }
    .rr { color: #f4f4f5; white-space: nowrap; font-weight: 600; }
    .rr s { color: #6b7280; font-weight: 400; }
    .rr em, .row em { font-style: normal; color: #4ade80; }
    .rr em.bad, .bad { color: #f87171; }
    .stars { display: flex; gap: 8px; margin-bottom: 10px; }
    .stars > div { flex: 1; background: rgba(255,255,255,.04); border-radius: 8px; padding: 8px; text-align: center; }
    .stars b { display: block; font-size: 10.5px; color: #9ca3af; text-transform: uppercase; letter-spacing: .03em; margin-bottom: 3px; }
    .star { font-size: 13px; font-weight: 700; color: #f4f4f5; }
    .star small { font-weight: 400; color: #9ca3af; }
    .star.muted { color: #6b7280; }
    .comp { padding: 8px 0; border-top: 1px solid #242428; }
    .comp:first-child { border-top: 0; }
    .comp-top { display: flex; justify-content: space-between; gap: 10px; }
    .comp-top a { color: #93c5fd; text-decoration: none; font-size: 12.5px; font-weight: 600; }
    .comp-top a:hover { text-decoration: underline; }
    .comp-sub { display: flex; align-items: center; gap: 8px; margin-top: 4px; flex-wrap: wrap; }
    .diff { font-size: 11.5px; color: #9ca3af; }
    .src { font-size: 11.5px; color: #93c5fd; text-decoration: none; }
    .src:hover { text-decoration: underline; }
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
