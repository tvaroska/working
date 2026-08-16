import { defineConfig } from 'vitest/config';

// Domain tests are pure TS (snake→camel mappers); node env is enough.
export default defineConfig({
  test: {
    environment: 'node',
    globals: true,
  },
});
