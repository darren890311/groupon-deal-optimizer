<script setup>
import { ref } from 'vue'
import { analyzeDeal } from './api'
import VerdictBanner from './components/VerdictBanner.vue'
import DiscountCard from './components/DiscountCard.vue'
import ReputationCard from './components/ReputationCard.vue'
import CompetitorsCard from './components/CompetitorsCard.vue'
import DirectBookingCard from './components/DirectBookingCard.vue'

const url = ref('')
const loading = ref(false)
const error = ref('')
const result = ref(null)

async function run() {
  if (!url.value.trim()) return
  loading.value = true
  error.value = ''
  result.value = null
  try {
    result.value = await analyzeDeal(url.value.trim())
  } catch (e) {
    error.value = e.message || 'Something went wrong.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="page">
    <header class="hero">
      <h1>Is this Groupon deal worth it?</h1>
      <p class="sub">Paste a Groupon deal link. We check the real discount, compare same-city prices, and cross-reference reviews.</p>
      <form class="bar" @submit.prevent="run">
        <input
          v-model="url"
          type="url"
          placeholder="https://www.groupon.com/deals/..."
          :disabled="loading"
        />
        <button type="submit" :disabled="loading || !url">
          {{ loading ? 'Analyzing…' : 'Analyze' }}
        </button>
      </form>
      <p v-if="loading" class="hint">Scraping the live page and similar deals — usually ~10s (instant if recently analyzed).</p>
      <p v-if="error" class="err">{{ error }}</p>
    </header>

    <main v-if="result" class="result">
      <p class="deal-title">
        {{ result.deal.title }}
        <span v-if="result.deal.merchant" class="muted"> · {{ result.deal.merchant }}<span v-if="result.deal.city">, {{ result.deal.city }}</span></span>
      </p>

      <VerdictBanner :verdict="result.verdict" :deal="result.deal" />

      <div class="grid">
        <DiscountCard :deal="result.deal" />
        <ReputationCard :reputation="result.reputation" />
      </div>

      <CompetitorsCard :competitors="result.competitors" :worth-buying="result.verdict.worth_buying" />
      <DirectBookingCard :direct-booking="result.direct_booking" />
    </main>
  </div>
</template>

<style scoped>
.page { max-width: 760px; margin: 0 auto; padding: 48px 20px 80px; }

.hero { text-align: center; margin-bottom: 36px; }
.hero h1 { font-size: 2rem; letter-spacing: -0.01em; }
.sub { color: var(--muted); max-width: 520px; margin: 12px auto 24px; }

.bar { display: flex; gap: 10px; max-width: 600px; margin: 0 auto; }
.bar input { flex: 1; }

.hint { color: var(--muted); font-size: 0.9rem; margin-top: 14px; }
.err {
  color: var(--bad-fg); background: var(--bad-bg); border: 1px solid var(--bad-line);
  border-radius: 10px; padding: 10px 14px; margin: 16px auto 0; max-width: 600px; font-size: 0.9rem;
}

.result { display: flex; flex-direction: column; gap: 16px; }
.deal-title { font-size: 1.05rem; font-weight: 600; margin: 0 2px; }

.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
@media (max-width: 620px) { .grid { grid-template-columns: 1fr; } }
</style>
