import { useCallback, useEffect, useRef, useState } from 'react';
import { Box, Button, Chip, Stack, TextField, Typography } from '@mui/material';
import { Panel, FollowupBadge } from '@bridge/shared';
import {
  mapTimewarp,
  type TimewarpView,
  type WireTimewarpState,
} from './domain/clock';

/**
 * Time-warp presenter control (no SSE — B4). Step / Advance N / Reset hit the
 * REST endpoints; "Play" is a browser `setInterval` calling `/advance` (the
 * server never runs a background timer). Advancing past the SLA deadline drives
 * `overdue → escalated` on the ops dashboard (shared virtual clock).
 */
export default function Timewarp() {
  const [state, setState] = useState<TimewarpView | null>(null);
  const [ticks, setTicks] = useState(1);
  const [playing, setPlaying] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(async () => {
    const res = await fetch('/timewarp/state');
    setState(mapTimewarp((await res.json()) as WireTimewarpState));
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const post = useCallback(async (path: string, body?: unknown) => {
    const res = await fetch(path, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
    });
    const json = (await res.json()) as { state: WireTimewarpState };
    setState(mapTimewarp(json.state));
  }, []);

  const step = useCallback(() => post('/timewarp/step'), [post]);
  const advance = useCallback(
    () => post('/timewarp/advance', { ticks }),
    [post, ticks],
  );
  const reset = useCallback(() => post('/timewarp/reset'), [post]);

  // "Play" = browser setInterval calling /advance (B4). Never e2e-tested.
  useEffect(() => {
    if (!playing) return;
    timerRef.current = setInterval(() => {
      void post('/timewarp/step');
    }, 1000);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [playing, post]);

  return (
    <Box>
      <Typography variant="h5" component="h1" gutterBottom>
        Time-warp
      </Typography>

      <Panel
        title={`Virtual clock: now = ${state?.now ?? '…'}`}
        action={
          state ? <FollowupBadge state={state.followup.state} /> : undefined
        }
        subtitle={
          state
            ? `SLA — deadline ${state.sla.deadline} · cadence ${state.sla.cadence} · max nudges ${state.sla.maxNudges}`
            : undefined
        }
      >
        <Stack
          direction="row"
          spacing={1}
          sx={{ alignItems: 'center', flexWrap: 'wrap' }}
        >
          <Button variant="outlined" onClick={step}>
            Step
          </Button>
          <TextField
            type="number"
            size="small"
            label="Ticks"
            value={ticks}
            onChange={(e) => setTicks(Math.max(0, Number(e.target.value)))}
            sx={{ width: 100 }}
            slotProps={{ htmlInput: { 'aria-label': 'ticks', min: 0 } }}
          />
          <Button variant="contained" onClick={advance}>
            Advance
          </Button>
          <Button
            variant="outlined"
            color={playing ? 'error' : 'primary'}
            onClick={() => setPlaying((p) => !p)}
          >
            {playing ? 'Pause' : 'Play'}
          </Button>
          <Button variant="text" onClick={reset}>
            Reset
          </Button>
        </Stack>
      </Panel>

      {state && (
        <Panel title="SLA timers">
          <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}>
            {state.timers.map((t) => (
              <Chip
                key={t.id}
                size="small"
                label={`${t.kind}#${t.sequence} @${t.fireAt}`}
                color={t.fired ? 'success' : 'default'}
                variant={t.fired ? 'filled' : 'outlined'}
              />
            ))}
          </Stack>
        </Panel>
      )}
    </Box>
  );
}
