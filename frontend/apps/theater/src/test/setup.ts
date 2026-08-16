import '@testing-library/jest-dom';

// jsdom implements neither EventSource nor fetch. The surfaces open an SSE
// connection / fetch on mount; provide inert stubs so component tests can render
// the shell without a live BFF (behavior is covered by the domain unit tests +
// Playwright e2e, not jsdom).
class MockEventSource {
  onerror: ((this: EventSource, ev: Event) => unknown) | null = null;
  addEventListener() {}
  removeEventListener() {}
  close() {}
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
(globalThis as any).EventSource = MockEventSource;

if (!('fetch' in globalThis)) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  (globalThis as any).fetch = async () =>
    ({
      ok: true,
      json: async () => ({}),
    }) as unknown as Response;
}
