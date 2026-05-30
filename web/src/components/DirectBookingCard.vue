<script setup>
const props = defineProps({ directBooking: Object })
</script>

<template>
  <div class="card" v-if="directBooking && directBooking.note">
    <h3>Booking direct</h3>
    <p class="note">
      <span v-if="directBooking.cheaper_than_groupon === true" class="flag ok">Direct is cheaper</span>
      <span v-else-if="directBooking.cheaper_than_groupon === false" class="flag bad">Groupon is cheaper</span>
      {{ directBooking.note }}
    </p>
    <a v-if="directBooking.source_url" :href="directBooking.source_url" target="_blank" rel="noopener">Source</a>
  </div>
</template>

<style scoped>
.note { margin: 0 0 8px; font-size: 0.92rem; }
.flag {
  display: inline-block; font-size: 0.72rem; font-weight: 700; text-transform: uppercase;
  padding: 2px 8px; border-radius: 999px; margin-right: 8px;
}
.flag.ok  { background: var(--ok-bg);  color: var(--ok-fg); }
.flag.bad { background: var(--bad-bg); color: var(--bad-fg); }
</style>
