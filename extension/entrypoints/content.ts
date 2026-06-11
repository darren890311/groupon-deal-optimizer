import { createApp } from 'vue';
import Panel from '@/components/Panel.vue';

// Inject the Revelio panel as a Vue app inside a shadow root, so Groupon's CSS
// can't leak in or out. The panel itself decides when to show (deal pages only)
// and re-arms on SPA navigation.
export default defineContentScript({
  matches: ['https://www.groupon.com/deals/*'],
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
