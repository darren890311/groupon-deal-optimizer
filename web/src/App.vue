<script setup>
// Chrome Web Store listing for the Revelio extension.
const STORE_URL = 'https://chromewebstore.google.com/detail/revelio-%E2%80%94-is-this-deal-ac/oggknnfgdnjbmkccjhahdffghldllocj'

const steps = [
  {
    n: '1',
    title: 'Add Revelio to Chrome',
    body: 'Install the free extension. No account, no signup - it stays out of your way until you need it.',
  },
  {
    n: '2',
    title: 'Open any Groupon deal',
    body: 'Revelio wakes up on the deal page and reads the offer, the price tiers, and the merchant.',
  },
  {
    n: '3',
    title: 'See buy, caution, or skip',
    body: 'A clear verdict in seconds: is the discount real, is the price fair, are the reviews honest, is it actually cheaper than booking direct?',
  },
]
</script>

<template>
  <div class="page">
    <!-- nav -->
    <nav class="nav">
      <a class="brand" href="/">
        <img src="/favicon.png" alt="" class="brand-logo" />
        <span>Revelio</span>
      </a>
      <a class="nav-cta" :href="STORE_URL" target="_blank" rel="noopener">Add to Chrome</a>
    </nav>

    <!-- hero -->
    <header class="hero">
      <h1>Is this Groupon deal <span class="hl">actually</span> a deal?</h1>
      <p class="sub">
        Revelio is a free browser assistant that checks whether a Groupon deal is worth buying - 
        the real discount, the fair price, honest reviews, and whether it's cheaper to book direct.
        Right on the deal page.
      </p>
      <a class="cta" :href="STORE_URL" target="_blank" rel="noopener">Add to Chrome - Free</a>
      <p class="cta-sub">Free · No signup · Not affiliated with Groupon</p>
    </header>

    <!-- product demo -->
    <section class="demo">
      <div class="frame">
        <div class="bar">
          <span class="dot r"></span><span class="dot y"></span><span class="dot g"></span>
        </div>
        <img src="/hero-demo.png" alt="Revelio panel open on a Groupon deal page" />
      </div>
    </section>

    <!-- how it works -->
    <section class="how">
      <h2>How it works</h2>
      <div class="steps">
        <div v-for="s in steps" :key="s.n" class="step">
          <div class="num">{{ s.n }}</div>
          <h3>{{ s.title }}</h3>
          <p>{{ s.body }}</p>
        </div>
      </div>
    </section>

    <footer class="foot">
      <span>© Revelio</span>
      <a href="/privacy.html">Privacy</a>
      <span class="muted">Not affiliated with Groupon.</span>
    </footer>
  </div>
</template>

<style scoped>
.page { max-width: 1040px; margin: 0 auto; padding: 0 20px 80px; }

/* nav */
.nav {
  display: flex; align-items: center; justify-content: space-between;
  padding: 20px 0;
}
.brand { display: flex; align-items: center; gap: 10px; color: var(--ink); font-weight: 700; font-size: 1.15rem; }
.brand:hover { text-decoration: none; }
.brand-logo { width: 30px; height: 30px; border-radius: 8px; }
.nav-cta {
  background: var(--brand); color: #fff; font-weight: 600;
  padding: 9px 18px; border-radius: 10px; font-size: 0.92rem;
}
.nav-cta:hover { opacity: 0.92; text-decoration: none; }

/* hero */
.hero { text-align: center; padding: 64px 0 40px; }
.hero h1 {
  font-size: 3rem; line-height: 1.08; letter-spacing: -0.02em;
  max-width: 760px; margin: 0 auto;
}
.hl { color: var(--brand); }
.sub {
  color: var(--muted); font-size: 1.12rem; max-width: 600px;
  margin: 22px auto 32px;
}
.cta {
  display: inline-block; background: var(--brand); color: #fff;
  font-weight: 700; font-size: 1.05rem; padding: 15px 34px;
  border-radius: 12px;
}
.cta:hover { opacity: 0.92; text-decoration: none; }
.cta-sub { color: var(--muted); font-size: 0.88rem; margin-top: 14px; }

/* product demo */
.demo { margin: 24px auto 0; max-width: 900px; }
.frame {
  background: var(--card); border: 1px solid var(--line);
  border-radius: 14px; overflow: hidden;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.45);
}
.frame .bar {
  display: flex; gap: 8px; padding: 12px 16px;
  background: #202020; border-bottom: 1px solid var(--line);
}
.dot { width: 11px; height: 11px; border-radius: 50%; }
.dot.r { background: #ff5f57; }
.dot.y { background: #febc2e; }
.dot.g { background: #28c840; }
.frame img { display: block; width: 100%; }

/* how it works */
.how { text-align: center; padding: 88px 0 0; }
.how h2 { font-size: 1.9rem; letter-spacing: -0.01em; }
.steps {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px;
  margin: 40px 0 44px; text-align: left;
}
.step {
  background: var(--card); border: 1px solid var(--line);
  border-radius: 14px; padding: 26px 24px;
}
.num {
  width: 36px; height: 36px; border-radius: 10px;
  background: var(--ok-bg); color: var(--ok-fg);
  display: flex; align-items: center; justify-content: center;
  font-weight: 700; margin-bottom: 16px;
}
.step h3 { font-size: 1.1rem; margin-bottom: 8px; }
.step p { color: var(--muted); font-size: 0.96rem; margin: 0; }

/* footer */
.foot {
  display: flex; gap: 18px; align-items: center; justify-content: center;
  margin-top: 80px; padding-top: 28px; border-top: 1px solid var(--line);
  color: var(--muted); font-size: 0.88rem;
}

@media (max-width: 720px) {
  .hero { padding: 40px 0 28px; }
  .hero h1 { font-size: 2.1rem; }
  .sub { font-size: 1rem; }
  .steps { grid-template-columns: 1fr; }
  .how { padding-top: 60px; }
}
</style>
