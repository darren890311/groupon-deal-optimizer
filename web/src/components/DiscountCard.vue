<script setup>
const props = defineProps({ deal: Object })

const VERDICT = {
  exaggerated: { cls: 'bad', text: 'Exaggerated' },
  honest: { cls: 'ok', text: 'Genuine' },
  none: { cls: 'warn', text: 'No real discount' },
}
function v() { return VERDICT[props.deal.discount_verdict] || VERDICT.none }
function pct(n) { return n == null ? ' - ' : `${Math.round(n)}%` }
</script>

<template>
  <div class="card">
    <h3>Discount truth</h3>
    <div class="rows">
      <div class="row">
        <span class="lbl">Advertised</span>
        <span class="val">{{ pct(deal.advertised_discount_pct) }}</span>
      </div>
      <div class="row">
        <span class="lbl">Actually displayed</span>
        <span class="val">{{ pct(deal.actual_max_discount_pct) }}</span>
      </div>
    </div>
    <span class="tag" :class="v().cls">{{ v().text }}</span>
  </div>
</template>

<style scoped>
.rows { display: flex; flex-direction: column; gap: 10px; margin-bottom: 16px; }
.row { display: flex; justify-content: space-between; align-items: baseline; }
.lbl { color: var(--muted); font-size: 0.92rem; }
.val { font-size: 1.5rem; font-weight: 700; }
.tag {
  display: inline-block;
  font-size: 0.82rem;
  font-weight: 700;
  padding: 5px 12px;
  border-radius: 999px;
}
.tag.ok   { background: var(--ok-bg);   color: var(--ok-fg); }
.tag.warn { background: var(--warn-bg); color: var(--warn-fg); }
.tag.bad  { background: var(--bad-bg);  color: var(--bad-fg); }
</style>
