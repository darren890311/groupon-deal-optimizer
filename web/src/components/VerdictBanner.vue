<script setup>
import { computed } from 'vue'
import { bookingUrl } from '../api'

const props = defineProps({ verdict: Object, deal: Object })

// "anyway" only reads right when we cautioned against the deal.
const bookLabel = computed(() =>
  props.verdict.worth_buying === 'yes' ? 'Buy on Groupon →' : 'Buy anyway on Groupon →',
)

const TONE = {
  yes: { cls: 'ok', label: 'Worth buying' },
  caution: { cls: 'warn', label: 'Buy with caution' },
  no: { cls: 'bad', label: 'Skip it' },
}

function tone(w) {
  return TONE[w] || TONE.caution
}
</script>

<template>
  <div class="banner" :class="tone(verdict.worth_buying).cls">
    <div class="verdict-tag">{{ tone(verdict.worth_buying).label }}</div>
    <p class="one-liner">{{ verdict.one_liner }}</p>

    <div class="badges">
      <span v-for="b in verdict.badges" :key="b.type" class="badge" :class="b.status">
        <span class="dot" />{{ b.label }}
      </span>
    </div>

    <p v-if="verdict.recommended_action" class="action">
      <strong>What to do:</strong> {{ verdict.recommended_action }}
    </p>

    <a
      v-if="deal && deal.url"
      class="book"
      :href="bookingUrl(deal.url)"
      target="_blank"
      rel="noopener"
    >{{ bookLabel }}</a>
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
  font-size: 0.78rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
.banner.ok .verdict-tag   { color: var(--ok-fg); }
.banner.warn .verdict-tag { color: var(--warn-fg); }
.banner.bad .verdict-tag  { color: var(--bad-fg); }

.one-liner {
  font-size: 1.3rem;
  font-weight: 600;
  margin: 8px 0 18px;
  line-height: 1.35;
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
  background: #fff;
  border: 1px solid var(--line);
}
.dot { width: 8px; height: 8px; border-radius: 50%; }
.badge.ok .dot   { background: var(--ok-fg); }
.badge.warn .dot { background: var(--warn-fg); }
.badge.bad .dot  { background: var(--bad-fg); }

.action { margin: 18px 0 0; font-size: 0.95rem; }

.book {
  display: inline-block;
  margin-top: 18px;
  padding: 10px 18px;
  border-radius: 10px;
  background: #53a318; /* Groupon green */
  border: 1px solid #53a318;
  color: #fff;
  font-weight: 600;
  font-size: 0.92rem;
}
.book:hover { text-decoration: none; background: #478c14; border-color: #478c14; }
</style>
