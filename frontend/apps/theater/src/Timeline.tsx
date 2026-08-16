import { useEffect, useMemo, useState } from 'react';
import { Alert, Box, Slider, Typography } from '@mui/material';
import { Panel, useSse } from '@bridge/shared';

/**
 * Timeline mode: the exchange as a **scrubbable event stream**. Frames from the
 * console stream are buffered into an event log; the slider replays them from
 * the buffer (no re-fetch).
 */
export default function Timeline() {
  const { frames, status } = useSse<Record<string, unknown>>(
    '/console/stream?scenario=sense-b',
    ['snapshot', 'turn'],
  );
  const [cursor, setCursor] = useState(0);

  // Keep the cursor at the latest frame as the stream fills.
  useEffect(() => {
    if (frames.length > 0) setCursor(frames.length - 1);
  }, [frames.length]);

  const current = useMemo(
    () => frames[Math.min(cursor, frames.length - 1)],
    [frames, cursor],
  );

  return (
    <Box>
      <Typography variant="h5" component="h1" gutterBottom>
        Timeline
      </Typography>

      {frames.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          {status === 'error' ? 'Stream error.' : 'Waiting for events…'}
        </Typography>
      ) : (
        <>
          <Box sx={{ px: 2, mb: 2 }}>
            <Slider
              min={0}
              max={frames.length - 1}
              value={Math.min(cursor, frames.length - 1)}
              onChange={(_e, v) => setCursor(v as number)}
              marks
              step={1}
              valueLabelDisplay="auto"
              aria-label="timeline scrubber"
            />
            <Typography variant="caption" color="text.secondary">
              Frame {Math.min(cursor, frames.length - 1) + 1} of {frames.length}
            </Typography>
          </Box>

          {current && (
            <Panel title={`Event: ${current.event}`}>
              <Alert severity="info" sx={{ mb: 1 }}>
                {current.event === 'snapshot'
                  ? 'Exchange opened.'
                  : current.event === 'turn'
                    ? `Collect round ${String((current.data as { round?: number }).round ?? '')}`
                    : 'Exchange settled.'}
              </Alert>
              <Box
                component="pre"
                sx={{
                  whiteSpace: 'pre-wrap',
                  fontSize: 12,
                  bgcolor: 'grey.100',
                  p: 1,
                  borderRadius: 1,
                  overflowX: 'auto',
                }}
              >
                {JSON.stringify(current.data, null, 2)}
              </Box>
            </Panel>
          )}
        </>
      )}
    </Box>
  );
}
