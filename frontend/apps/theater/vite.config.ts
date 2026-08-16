import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { configDefaults } from 'vitest/config';

// The host shell hosts all four surfaces as routed modules (single-host-shell
// deviation from §C2's "one Vite dev server per surface" — see README). The dev
// proxy forwards each surface prefix to its BFF server port (§C2).
export default defineConfig({
  server: {
    proxy: {
      '/console': 'http://localhost:8010',
      '/ops': 'http://localhost:8011',
      '/portal': 'http://localhost:8012',
      '/timewarp': 'http://localhost:8013',
    },
  },
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.ts',
    exclude: [...configDefaults.exclude, 'e2e/**'],
  },
});
