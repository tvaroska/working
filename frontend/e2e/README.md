# Playwright e2e — SSE stubbing (lessons B1 / B2)

The Split-Screen Theater arc is driven end-to-end against **stubbed** BFF
endpoints so it is deterministic in CI (no live uvicorn servers, no fixture
engine, no virtual clock in the browser).

## B1 — the one-shot SSE stub

Playwright's `page.route` fulfills a request **one-shot**, but the browser's
`EventSource` expects a live `text/event-stream`. The trick in `sse.ts`: deliver
the **entire** scripted stream — every `snapshot`/`turn`/`event` frame **plus the
terminal `done`** — as a **single response body**. Because the client closes the
connection when it sees `done`, the natural end-of-body never triggers a
reconnect.

```ts
await page.route('**/console/stream*', (route) =>
  fulfillSse(route, [
    ['snapshot', { rule: '…' }],
    ['turn', { round: 1 /* … */ }],
  ]),
);
```

## B2 — client close discipline

The shared `useSse` hook sets a `finished` flag when it receives `done`, then
closes the `EventSource`. The expected server-side close after `done` is
therefore **not** surfaced as an error and never reconnects. The Python SSE
emitters mirror this: they emit a terminal `done` event, then close cleanly.

## B4 — time-warp has no SSE

The time-warp endpoints are plain REST (stubbed with `fulfillJson`). "Play" is a
browser `setInterval` and is intentionally **not** e2e-tested (timer-driven,
flaky); the arc uses an explicit **Advance** click instead.
