<script setup>
import { computed } from 'vue'

const props = defineProps({ competitors: Array, worthBuying: String })

// Honor the UX rule: for a weak deal lead with alternatives; for a good deal the
// list is supporting evidence. Data is always shown either way.
const heading = computed(() =>
  props.worthBuying === 'yes'
    ? 'How it compares (same-city)'
    : 'Cheaper / comparable options nearby',
)

const sorted = computed(() =>
  [...(props.competitors || [])].sort((a, b) => (b.cheaper ? 1 : 0) - (a.cheaper ? 1 : 0)),
)

function price(n) { return n == null ? '—' : `$${n}` }
</script>

<template>
  <div class="card" v-if="competitors && competitors.length">
    <h3>{{ heading }}</h3>
    <ul class="list">
      <li v-for="c in sorted" :key="c.url || c.merchant" class="comp">
        <div class="top">
          <a v-if="c.url" :href="c.url" target="_blank" rel="noopener" class="name">{{ c.merchant }}</a>
          <span v-else class="name">{{ c.merchant }}</span>
          <span class="price" :class="{ cheap: c.cheaper }">{{ price(c.price) }}</span>
        </div>
        <div class="meta">
          <span class="match" :class="c.match">{{ c.match }}</span>
          <span v-if="c.cheaper" class="cheap-tag">cheaper</span>
          <span v-if="c.difference_note" class="diff">{{ c.difference_note }}</span>
        </div>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 14px; }
.comp { border-bottom: 1px solid var(--line); padding-bottom: 12px; }
.comp:last-child { border-bottom: none; padding-bottom: 0; }
.top { display: flex; justify-content: space-between; align-items: baseline; gap: 10px; }
.name { font-weight: 600; }
.price { font-weight: 700; white-space: nowrap; }
.price.cheap { color: var(--ok-fg); }
.meta { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; margin-top: 5px; }
.match {
  font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.03em;
  padding: 2px 8px; border-radius: 999px;
}
.match.same    { background: var(--ok-bg);   color: var(--ok-fg); }
.match.similar { background: var(--warn-bg); color: var(--warn-fg); }
.cheap-tag {
  font-size: 0.72rem; font-weight: 700; color: var(--ok-fg);
  background: var(--ok-bg); padding: 2px 8px; border-radius: 999px;
}
.diff { font-size: 0.85rem; color: var(--muted); }
</style>
