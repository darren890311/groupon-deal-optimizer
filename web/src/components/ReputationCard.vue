<script setup>
const props = defineProps({ reputation: Object })
function star(n) { return n == null ? '—' : `${n}★` }
</script>

<template>
  <div class="card">
    <h3>Reputation across platforms</h3>
    <div class="cmp">
      <div class="side">
        <div class="score">{{ star(reputation.groupon_rating) }}</div>
        <div class="src">Groupon<span v-if="reputation.groupon_reviews"> · {{ reputation.groupon_reviews }} reviews</span></div>
      </div>
      <div class="vs">vs</div>
      <div class="side">
        <div class="score">{{ star(reputation.external_rating) }}</div>
        <div class="src">{{ reputation.external_source || 'External' }}<span v-if="reputation.external_reviews"> · {{ reputation.external_reviews }} reviews</span></div>
      </div>
    </div>
    <p class="summary">{{ reputation.summary }}</p>
  </div>
</template>

<style scoped>
.cmp { display: flex; align-items: center; gap: 16px; margin-bottom: 14px; }
.side { flex: 1; text-align: center; }
.score { font-size: 1.8rem; font-weight: 700; }
.src { font-size: 0.82rem; color: var(--muted); margin-top: 2px; }
.vs { color: var(--muted); font-size: 0.85rem; font-weight: 600; }
.summary { font-size: 0.92rem; color: var(--ink); margin: 0; }
</style>
