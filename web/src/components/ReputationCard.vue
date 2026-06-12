<script setup>
import { computed } from 'vue'

const props = defineProps({ reputation: Object })

const platforms = computed(() => {
  const r = props.reputation || {}
  return [
    { name: 'Groupon', rating: r.groupon_rating, reviews: r.groupon_reviews, external: false },
    { name: 'Google', rating: r.google_rating, reviews: r.google_reviews, external: true },
    { name: 'Yelp', rating: r.yelp_rating, reviews: r.yelp_reviews, external: true },
  ]
})

// Subtitle under each score. A bare review count with no star reads as broken,
// so only show the count when we actually have a rating; otherwise say why not.
function caption(p) {
  if (p.rating != null) return p.reviews != null ? p.reviews + ' reviews' : ''
  if (p.external && props.reputation?.chain) return 'varies by location'
  return 'no rating found'
}
</script>

<template>
  <div class="card">
    <h3>Reputation across platforms</h3>
    <div class="row">
      <div v-for="p in platforms" :key="p.name" class="plat">
        <div class="score" :class="{ none: p.rating == null }">
          {{ p.rating == null ? ' - ' : p.rating }}<span v-if="p.rating != null" class="star">★</span>
        </div>
        <div class="name">{{ p.name }}</div>
        <div class="rev">{{ caption(p) }}</div>
      </div>
    </div>
    <p v-if="reputation.summary" class="summary">{{ reputation.summary }}</p>
  </div>
</template>

<style scoped>
.row { display: flex; gap: 10px; margin-bottom: 14px; }
.plat { flex: 1; text-align: center; }
.score { font-size: 1.7rem; font-weight: 700; line-height: 1.1; }
.score.none { color: var(--muted); }
.star { color: #f5b301; font-size: 1.2rem; margin-left: 1px; }
.name { font-size: 0.9rem; font-weight: 600; margin-top: 4px; }
.rev { font-size: 0.75rem; color: var(--muted); margin-top: 2px; }
.summary { font-size: 0.92rem; color: var(--ink); margin: 0; }
</style>
