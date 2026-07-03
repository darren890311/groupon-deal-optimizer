<script setup lang="ts">
import { computed } from 'vue';
import Section from './Section.vue';
import { money } from '@/utils/format';

const props = defineProps<{ data: any }>();

const TONE: Record<string, { cls: string; label: string; icon: string }> = {
  yes: { cls: 'ok', label: 'Worth buying', icon: '✓' },
  caution: { cls: 'warn', label: 'Buy with caution', icon: '⚠' },
  no: { cls: 'bad', label: 'Not worth it', icon: '✕' },
};
const DISCOUNT: Record<string, { cls: string; word: string }> = {
  honest: { cls: 'ok', word: 'genuine' },
  exaggerated: { cls: 'bad', word: 'exaggerated' },
  none: { cls: 'warn', word: 'no real discount' },
};
const GAP: Record<string, { cls: string; text: string }> = {
  consistent: { cls: 'ok', text: 'consistent' },
  external_higher: { cls: 'ok', text: 'external higher' },
  external_lower: { cls: 'bad', text: 'external lower' },
  divergent: { cls: 'warn', text: 'ratings disagree' },
  insufficient: { cls: 'warn', text: 'limited data' },
};
const MATCH: Record<string, string> = { same: 'ok', similar: 'warn', different: 'muted' };

const v = computed(() => props.data.verdict || {});
const deal = computed(() => props.data.deal || {});
const rep = computed(() => props.data.reputation);
const comps = computed<any[]>(() => props.data.competitors || []);
const db = computed(() => props.data.direct_booking);

const tone = computed(() => TONE[v.value.worth_buying] || TONE.caution);

// Pill must reflect the actual discount BADGE (which includes the fake-anchor
// override: "direct is cheaper" flips discount to bad even when Groupon's own
// strike-through math is honest). Reading deal.discount_verdict alone makes the
// section say "genuine" while the headline badge says "Not a real deal".
const discountBadge = computed<any>(() => (v.value.badges || []).find((b: any) => b.type === 'discount'));
const dv = computed(() => {
  const b = discountBadge.value;
  if (!b) return DISCOUNT[deal.value.discount_verdict] || { cls: 'warn', word: deal.value.discount_verdict || '-' };
  if (b.status === 'ok') return { cls: 'ok', word: 'genuine' };
  if (b.status === 'bad') return { cls: 'bad', word: deal.value.discount_verdict === 'exaggerated' ? 'exaggerated' : 'no real discount' };
  return { cls: 'warn', word: 'no real discount' };
});
// "up to X%" only means something when the discount is genuine; on a fake-anchor
// deal the on-Groupon % is real but meaningless, so don't show it.
const maxText = computed(() =>
  dv.value.cls === 'ok' && deal.value.actual_max_discount_pct != null
    ? `up to ${Math.round(deal.value.actual_max_discount_pct)}%`
    : '',
);
const claimText = computed(() =>
  deal.value.advertised_discount_pct != null
    ? `Headline claim: ${Math.round(deal.value.advertised_discount_pct)}% · `
    : 'No headline % claim · ',
);

const repTag = computed(() => {
  if (!rep.value) return { cls: 'warn', text: '-' };
  if (rep.value.chain) return { cls: 'warn', text: 'varies by location' };
  return GAP[rep.value.gap_verdict] || { cls: 'warn', text: rep.value.gap_verdict || '-' };
});
const platforms = computed(() =>
  rep.value
    ? [
        { name: 'Groupon', r: rep.value.groupon_rating, n: rep.value.groupon_reviews },
        { name: 'Google', r: rep.value.google_rating, n: rep.value.google_reviews },
      ].filter((p) => p.r != null)
    : [],
);

const anyCheaper = computed(() => comps.value.some((c) => c.cheaper));

const directTag = computed(() => {
  const c = db.value?.cheaper_than_groupon;
  return c === true
    ? { cls: 'warn', text: 'may be cheaper' }
    : c === false
      ? { cls: 'ok', text: 'Groupon wins' }
      : { cls: 'muted', text: 'verify price' };
});

const round = (n: number) => Math.round(n);
const fmtCount = (n: number) => Number(n).toLocaleString();
const fmtRating = (r: number) => Number(r).toFixed(1);
</script>

<template>
  <div class="verdict" :class="tone.cls">
    <div class="vtag"><span class="vicon">{{ tone.icon }}</span>{{ tone.label }}</div>
    <p v-if="deal.title" class="dtitle">{{ deal.title }}</p>
    <p class="oneliner">{{ v.one_liner }}</p>
    <div v-if="v.badges && v.badges.length" class="badges">
      <span v-for="b in v.badges" :key="b.type" class="badge" :class="b.status"><i></i>{{ b.label }}</span>
    </div>
    <p v-if="v.recommended_action" class="action"><b>What to do:</b> {{ v.recommended_action }}</p>
  </div>

  <div class="sections">
    <!-- Discount -->
    <Section title="Discount">
      <template #takeaway><span class="pill" :class="dv.cls">{{ dv.word }}</span> {{ maxText }}</template>
      <p class="note">{{ claimText }}real strike-through per option:</p>
      <div v-for="(p, i) in (deal.prices || [])" :key="i" class="row">
        <span class="rl">{{ p.label || 'Option' }}</span>
        <span class="rr">
          <s v-if="p.original != null">{{ money(p.original) }}</s> {{ money(p.deal) }}<em v-if="p.discount_pct != null"> -{{ round(p.discount_pct) }}%</em>
        </span>
      </div>
    </Section>

    <!-- Reputation -->
    <Section v-if="rep" title="Reputation">
      <template #takeaway><span class="pill" :class="repTag.cls">{{ repTag.text }}</span></template>
      <div class="stars">
        <div v-for="p in platforms" :key="p.name">
          <b>{{ p.name }}</b>
          <span v-if="p.r != null" class="star">{{ fmtRating(p.r) }}★<small v-if="p.n != null"> ({{ fmtCount(p.n) }})</small></span>
          <span v-else class="star muted">-</span>
        </div>
      </div>
      <p v-if="rep.summary" class="note">{{ rep.summary }}</p>
    </Section>

    <!-- Competitors -->
    <Section title="Competitors">
      <template #takeaway>
        <span v-if="!comps.length" class="pill muted">none found</span>
        <span v-else class="pill" :class="anyCheaper ? 'warn' : 'ok'">{{ comps.length }} found{{ anyCheaper ? ' · cheaper exists' : '' }}</span>
      </template>
      <p v-if="!comps.length" class="note">No comparable same-city deals found.</p>
      <div v-for="(c, i) in comps" :key="i" class="comp">
        <div class="comp-top">
          <a :href="c.url || '#'" target="_blank" rel="noopener">{{ c.merchant || c.title || '-' }}</a>
          <span class="rr">{{ money(c.price) }}<em v-if="c.cheaper" class="bad"> cheaper ↓</em></span>
        </div>
        <div class="comp-sub">
          <span class="pill" :class="MATCH[c.match] || 'muted'">{{ c.match || '-' }}</span>
          <span v-if="c.difference_note" class="diff">{{ c.difference_note }}</span>
        </div>
      </div>
    </Section>

    <!-- Direct booking -->
    <Section v-if="db" title="Direct booking">
      <template #takeaway><span class="pill" :class="directTag.cls">{{ directTag.text }}</span></template>
      <p v-if="db.note" class="note">{{ db.note }}</p>
      <a v-if="db.source_url" class="src" :href="db.source_url" target="_blank" rel="noopener">source ↗</a>
    </Section>
  </div>
</template>
