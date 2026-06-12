import { createApp } from 'vue';
import Panel from '@/components/Panel.vue';

// Inject the Revelio panel as a Vue app inside a shadow root, so Groupon's CSS
// can't leak in or out. The panel itself decides when to show (deal pages only,
// via isDealPage) and re-arms on SPA navigation.
//
// We match ALL of www.groupon.com, not just /deals/*, because Groupon is a SPA:
// arriving at a deal by clicking from the homepage is a client-side route change
// with no document load, so a /deals/* content script would never inject (it only
// appeared after a manual refresh). Injecting site-wide lets the panel stay
// hidden on non-deal pages and reveal itself when SPA navigation lands on a deal.
export default defineContentScript({
  matches: ['https://www.groupon.com/*'],
  cssInjectionMode: 'ui',
  async main(ctx) {
    const ui = await createShadowRootUi(ctx, {
      name: 'revelio-panel',
      position: 'overlay',
      anchor: 'body',
      append: 'last',
      onMount(container) {
        const app = createApp(Panel);
        app.mount(container);
        return app;
      },
      onRemove(app) {
        app?.unmount();
      },
    });
    ui.mount();
  },
});
