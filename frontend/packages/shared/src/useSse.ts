import { useEffect, useRef, useState } from 'react';

export type SseStatus = 'connecting' | 'streaming' | 'done' | 'error';

export interface SseFrame<T = unknown> {
  event: string;
  data: T;
}

export interface UseSseResult<T = unknown> {
  frames: SseFrame<T>[];
  status: SseStatus;
  error: string | null;
}

/**
 * SSE client hook with **close discipline** (lessons B2).
 *
 * Every Bridge SSE stream ends with a terminal `done` event; the server then
 * closes the connection cleanly. Without care, `EventSource` treats that
 * expected close as an error and tries to reconnect. This hook sets a `finished`
 * flag on `done` so the expected close never surfaces as an error and never
 * reconnects.
 *
 * @param url The SSE endpoint (e.g. `/console/stream?scenario=sense-b`).
 * @param events Named events to listen for besides the terminal `done`
 *   (e.g. `['snapshot', 'turn']`). All are collected into `frames` in order.
 */
export function useSse<T = unknown>(
  url: string | null,
  events: string[],
): UseSseResult<T> {
  const [frames, setFrames] = useState<SseFrame<T>[]>([]);
  const [status, setStatus] = useState<SseStatus>('connecting');
  const [error, setError] = useState<string | null>(null);
  // Stable key so the effect only re-runs when the wire inputs change.
  const eventsKey = events.join(',');

  const finishedRef = useRef(false);

  useEffect(() => {
    if (!url) return;

    finishedRef.current = false;
    setFrames([]);
    setError(null);
    setStatus('connecting');

    const source = new EventSource(url);
    const listened = eventsKey ? eventsKey.split(',') : [];

    const push = (event: string) => (e: MessageEvent) => {
      setStatus('streaming');
      let data: T;
      try {
        data = JSON.parse(e.data) as T;
      } catch {
        data = e.data as unknown as T;
      }
      setFrames((prev) => [...prev, { event, data }]);
    };

    for (const name of listened) {
      source.addEventListener(name, push(name));
    }

    source.addEventListener('done', (e: MessageEvent) => {
      // Record the terminal frame, then close cleanly (B2).
      let data: T;
      try {
        data = JSON.parse(e.data) as T;
      } catch {
        data = e.data as unknown as T;
      }
      setFrames((prev) => [...prev, { event: 'done', data }]);
      finishedRef.current = true;
      setStatus('done');
      source.close();
    });

    source.onerror = () => {
      // The expected close after `done` is not an error (B2).
      if (finishedRef.current) return;
      setStatus('error');
      setError('SSE connection error');
      source.close();
    };

    return () => {
      finishedRef.current = true;
      source.close();
    };
  }, [url, eventsKey]);

  return { frames, status, error };
}
