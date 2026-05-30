<script setup>
import { computed } from 'vue'

const props = defineProps({ competitors: Array, worthBuying: String })

// Only genuine alternatives: same-service deals (any price — they show whether
// you're paying a fair rate) plus cheaper "similar" ones. A pricier, non-identical
// option is not an alternative, so it's hidden rather than shown as "comparable".
const visible = computed(() =>
  [...(props.competitors || [])]
    .filter((c) => c.match === 'same' || c.cheaper)
    .sort((a, b) => (b.cheaper ? 1 : 0) - (a.cheaper ? 1 : 0)),
)

function price(n) { return n == null ? '—' : `$${n}` }
</script>

<template>
  <div class="card" v-if="visible.length">
    <h3>Same-city price comparison</h3>
    <ul class="list">
      <li v-for="c in visible" :key="c.url || c.merchant" class="comp">
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
