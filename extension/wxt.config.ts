import { defineConfig } from 'wxt';

// WXT auto-generates the manifest: content_scripts come from entrypoints/content.ts,
// the service worker from entrypoints/background.ts, icons from public/icon/*, and
// web_accessible_resources from assets imported in the content script.
export default defineConfig({
  modules: ['@wxt-dev/module-vue'],
  manifest: ({ mode }) => ({
    name: 'Revelio — Is This Deal Actually A Deal?',
    // Kept under Chrome's 132-char limit; includes the not-affiliated disclaimer.
    description:
      'Independent deal checker for Groupon — real discount, same-city prices, cross-platform ratings. Not affiliated with Groupon.',
    host_permissions: [
      'https://groupon-api-xklyudhzbq-uc.a.run.app/*',
      // localhost is dev-only — excluded from the production / Chrome Web Store build.
      ...(mode === 'development' ? ['http://127.0.0.1:8080/*'] : []),
    ],
  }),
});
