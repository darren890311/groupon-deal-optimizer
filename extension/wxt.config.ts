import { defineConfig } from 'wxt';

// WXT auto-generates the manifest: content_scripts come from entrypoints/content.ts,
// the service worker from entrypoints/background.ts, icons from public/icon/*, and
// web_accessible_resources from assets imported in the content script.
export default defineConfig({
  modules: ['@wxt-dev/module-vue'],
  manifest: {
    name: 'Revelio — Is This Deal Actually A Deal?',
    description:
      "On a Groupon deal page, reveal whether it's actually a good buy: the real discount, like-for-like prices, and cross-platform ratings.",
    permissions: ['storage'],
    host_permissions: [
      'https://groupon-api-xklyudhzbq-uc.a.run.app/*',
      'http://127.0.0.1:8080/*',
    ],
  },
});
