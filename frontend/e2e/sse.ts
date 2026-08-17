import type { Route } from '@playwright/test';

/**
 * One-shot SSE stub for Playwright (lessons B1).
 *
 * Playwright's `page.route` fulfills a request **once**, but `EventSource` wants
 * a live `text/event-stream`. The working trick: deliver the **entire** scripted
 * stream — every `snapshot`/`turn`/`event` frame plus the terminal `done` — as a
 * **single response body**. The client (see `@bridge/shared` `useSse`) closes on
 * `done`, so the connection-end never triggers a reconnect (B2). This lets us
 * script a whole SSE arc without a live BFF server.
 */

export type SseFrame = [event: string, data: unknown];

/** Serialize scripted frames into one `text/event-stream` body (incl. `done`). */
export function sseBody(frames: SseFrame[]): string {
  return (
    frames
      .map(
        ([event, data]) => `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`,
      )
      .join('') + 'event: done\ndata: {"outcome":"done"}\n\n'
  );
}

/** Fulfill an SSE route with the whole scripted stream as one body (B1). */
export async function fulfillSse(route: Route, frames: SseFrame[]) {
  await route.fulfill({
    status: 200,
    headers: {
      'content-type': 'text/event-stream; charset=utf-8',
      'cache-control': 'no-cache',
    },
    body: sseBody(frames),
  });
}

/** Fulfill a plain JSON (REST) route. */
export async function fulfillJson(route: Route, data: unknown) {
  await route.fulfill({
    status: 200,
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(data),
  });
}
