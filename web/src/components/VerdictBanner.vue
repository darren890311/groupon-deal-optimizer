<script setup>
defineProps({ verdict: Object, deal: Object })

const TONE = {
  yes: { cls: 'ok', label: 'Worth buying', icon: '✓' },
  caution: { cls: 'warn', label: 'Buy with caution', icon: '⚠' },
  no: { cls: 'bad', label: 'Not worth it', icon: '✕' },
}

function tone(w) {
  return TONE[w] || TONE.caution
}
</script>

<template>
  <div class="banner" :class="tone(verdict.worth_buying).cls">
    <div class="verdict-tag">
      <span class="vicon">{{ tone(verdict.worth_buying).icon }}</span>{{ tone(verdict.worth_buying).label }}
    </div>
    <p class="one-liner">{{ verdict.one_liner }}</p>

    <div class="badges">
      <span v-for="b in verdict.badges" :key="b.type" class="badge" :class="b.status">
        <span class="dot" />{{ b.label }}
      </span>
    </div>

    <p v-if="verdict.recommended_action" class="action">
      <strong>What to do:</strong> {{ verdict.recommended_action }}
    </p>
  </div>
</template>

<style scoped>
.banner {
  border-radius: 16px;
  padding: 24px 26px;
  border: 1px solid;
}
.banner.ok   { background: var(--ok-bg);   border-color: var(--ok-line); }
.banner.warn { background: var(--warn-bg); border-color: var(--warn-line); }
.banner.bad  { background: var(--bad-bg);  border-color: var(--bad-line); }

.verdict-tag {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 1.6rem;
  font-weight: 750;
  letter-spacing: -0.01em;
}
.vicon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  font-size: 0.95rem;
  color: #fff;
  flex: none;
}
.banner.ok .verdict-tag   { color: var(--ok-fg); }
.banner.warn .verdict-tag { color: var(--warn-fg); }
.banner.bad .verdict-tag  { color: var(--bad-fg); }
.banner.ok .vicon   { background: var(--ok-fg); }
.banner.warn .vicon { background: var(--warn-fg); }
.banner.bad .vicon  { background: var(--bad-fg); }

.one-liner {
  font-size: 1.05rem;
  font-weight: 500;
  margin: 10px 0 18px;
  line-height: 1.45;
}

.badges { display: flex; flex-wrap: wrap; gap: 8px; }
.badge {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 0.85rem;
  font-weight: 600;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
}
.dot { width: 8px; height: 8px; border-radius: 50%; }
.badge.ok .dot   { background: var(--ok-fg); }
.badge.warn .dot { background: var(--warn-fg); }
.badge.bad .dot  { background: var(--bad-fg); }

.action { margin: 18px 0 0; font-size: 0.95rem; }
</style>
