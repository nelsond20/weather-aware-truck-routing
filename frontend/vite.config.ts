import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'node:url';
import { playwright } from '@vitest/browser-playwright';
import { storybookTest } from '@storybook/addon-vitest/vitest-plugin';
export default defineConfig({
  plugins: [react()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  server: { host: '127.0.0.1', proxy: { '/api': 'http://127.0.0.1:8000' } },
  build: { sourcemap: false },
  test: { restoreMocks: true, projects: [
    { extends: true, test: { name: 'unit', environment: 'node', include: ['src/**/*.test.ts'], setupFiles: ['src/test/setup.ts'] } },
    { extends: true, test: { name: 'hooks', environment: 'jsdom', include: ['src/**/*.test.tsx'] } },
    { extends: true, plugins: [storybookTest({ configDir: fileURLToPath(new URL('./.storybook', import.meta.url)), storybookScript: 'npm run storybook -- --ci' })],
      optimizeDeps: { include: ['react','react-dom','react-dom/client','react/jsx-runtime','react/jsx-dev-runtime','msw-storybook-addon/csf3','msw/browser','storybook/test','@storybook/addon-a11y/preview'] },
      test: { name: 'stories', browser: { enabled: true, provider: playwright({ launchOptions: { args: ['--no-sandbox'] } }), headless: true, instances: [{ browser: 'chromium' }] }, setupFiles: ['.storybook/vitest.setup.ts'] } },
  ] },
});
