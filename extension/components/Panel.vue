<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import Verdict from './Verdict.vue';
import { analyze } from '@/utils/api';
import { isDealPage } from '@/utils/page';
import logo from '@/assets/logo.png';

type View = 'prompt' | 'loading' | 'verdict' | 'error' | 'collapsed';

const view = ref<View>('prompt');
const result = ref<any>(null);
const errorMsg = ref('');
const onDeal = ref(isDealPage());

const headerTitle = computed(
  () =>
    ({
      prompt: 'Is this deal actually a deal?',
      loading: 'Revealing…',
      error: "Couldn't reveal",
      verdict: 'Revelio',
      collapsed: 'Revelio',
    })[view.value],
);

function reveal() {
  view.value = 'loading';
  analyze()
    .then((data) => {
      result.value = data;
      view.value = 'verdict';
    })
    .catch((e) => {
      errorMsg.value = e?.message || 'Something went wrong.';
      view.value = 'error';
    });
}

// Groupon is a single-page app: a deal→deal navigation doesn't reload the
// content script, so poll the URL and re-arm the prompt when it changes.
let lastHref = location.href;
let timer: ReturnType<typeof setInterval> | undefined;
onMounted(() => {
  timer = setInterval(() => {
    if (location.href !== lastHref) {
      lastHref = location.href;
      onDeal.value = isDealPage();
      view.value = 'prompt';
      result.value = null;
    }
  }, 1000);
});
onUnmounted(() => clearInterval(timer));
</script>

<template>
  <div v-if="onDeal" class="wrap">
    <button v-if="view === 'collapsed'" class="tab" title="Open Revelio" @click="view = 'prompt'">
      <img :src="logo" alt="Revelio" />
    </button>

    <div v-else class="card">
      <div class="hd">
        <span class="brand"><img :src="logo" alt="" />{{ headerTitle }}</span>
        <button class="x" title="Close" @click="view = 'collapsed'">✕</button>
      </div>

      <template v-if="view === 'prompt'">
        <p class="lede">Revelio checks the <b>real</b> discount, compares same-city prices, and cross-references Yelp/Google ratings.</p>
        <button class="cta reveal" @click="reveal">✨ Reveal this deal</button>
      </template>

      <div v-else-if="view === 'loading'" class="loading">
        <img :src="logo" class="spin" alt="" />
        <p class="lede">Reading the deal, finding similar ones, checking ratings, usually ~10s.</p>
      </div>

      <template v-else-if="view === 'error'">
        <p class="lede err">{{ errorMsg }}</p>
        <button class="cta reveal" @click="reveal">Try again</button>
      </template>

      <Verdict v-else-if="view === 'verdict'" :data="result" />
    </div>
  </div>
</template>

<style>
/* Non-scoped on purpose: the shadow root isolates these from Groupon's page. */
.wrap {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 2147483647;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}
.card {
  width: 340px;
  background: #1a1a1a;
  color: #f4f4f5;
  border: 1px solid #2e2e32;
  border-radius: 16px;
  padding: 16px 18px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.45);
  max-height: calc(100vh - 32px);
  overflow-y: auto;
  overscroll-behavior: contain;
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
  display: block;
  width: 100%;
  text-align: center;
  box-sizing: border-box;
  padding: 10px 14px;
  border-radius: 10px;
  border: 0;
  cursor: pointer;
  font-weight: 650;
  font-size: 14px;
}
.reveal { background: #53a318; color: #fff; }
.reveal:hover { background: #478c14; }
.loading { display: flex; flex-direction: column; align-items: center; gap: 12px; padding: 6px 0 2px; }
.spin { width: 44px; height: 44px; border-radius: 10px; animation: spin 1.4s linear infinite; }
@keyframes spin { to { transform: rotateY(360deg); } }
.loading .lede { text-align: center; margin: 0; }
.tab {
  width: 46px;
  height: 46px;
  border-radius: 50%;
  border: 1px solid #2e2e32;
  background: #1a1a1a;
  cursor: pointer;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
}
.tab img { width: 26px; height: 26px; border-radius: 7px; }
.verdict { border-radius: 12px; }
.vtag { display: flex; align-items: center; gap: 9px; font-size: 18px; font-weight: 750; }
.vicon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  font-size: 13px;
  color: #fff;
  flex: none;
}
.verdict.ok .vtag { color: #4ade80; }
.verdict.ok .vicon { background: #16a34a; }
.verdict.warn .vtag { color: #fbbf24; }
.verdict.warn .vicon { background: #d97706; }
.verdict.bad .vtag { color: #f87171; }
.verdict.bad .vicon { background: #dc2626; }
.dtitle { font-size: 13px; font-weight: 600; margin: 10px 0 4px; color: #e5e7eb; }
.oneliner { font-size: 13.5px; line-height: 1.5; margin: 8px 0 12px; }
.badges { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 4px; }
.badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 11.5px;
  font-weight: 600;
  padding: 4px 9px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
}
.badge i { width: 7px; height: 7px; border-radius: 50%; }
.badge.ok i { background: #4ade80; }
.badge.warn i { background: #fbbf24; }
.badge.bad i { background: #f87171; }
.action { font-size: 12.5px; line-height: 1.5; margin: 12px 0 0; color: #cbced4; }

/* collapsible detail sections */
.sections { margin: 14px 0 4px; border-top: 1px solid #2e2e32; }
details { border-bottom: 1px solid #2e2e32; }
summary {
  list-style: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 2px;
  font-size: 12.5px;
}
summary::-webkit-details-marker { display: none; }
.st { font-weight: 650; color: #f4f4f5; }
.chev { margin-left: auto; color: #9ca3af; transition: transform 0.15s; }
details[open] .chev { transform: rotate(90deg); }
.sbody { padding: 2px 2px 12px; }
.pill {
  font-size: 11px;
  font-weight: 650;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  white-space: nowrap;
}
.pill.ok { color: #4ade80; }
.pill.warn { color: #fbbf24; }
.pill.bad { color: #f87171; }
.pill.muted { color: #9ca3af; }
.note { font-size: 12px; line-height: 1.5; color: #cbced4; margin: 0 0 8px; }
.row { display: flex; justify-content: space-between; gap: 10px; font-size: 12px; padding: 4px 0; border-top: 1px solid #242428; }
.rl { color: #cbced4; flex: 1; }
.rr { color: #f4f4f5; white-space: nowrap; font-weight: 600; }
.rr s { color: #6b7280; font-weight: 400; }
.rr em, .row em { font-style: normal; color: #4ade80; }
.rr em.bad, .bad { color: #f87171; }
.stars { display: flex; gap: 8px; margin-bottom: 10px; }
.stars > div { flex: 1; background: rgba(255, 255, 255, 0.04); border-radius: 8px; padding: 8px; text-align: center; }
.stars b { display: block; font-size: 10.5px; color: #9ca3af; text-transform: uppercase; letter-spacing: 0.03em; margin-bottom: 3px; }
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
</style>
