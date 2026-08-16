import { useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Chip,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import {
  Panel,
  DispositionBadge,
  RequirementBadge,
  DoneBadge,
  useSse,
  type SseFrame,
} from '@bridge/shared';
import { mapTurn, type WireTurn } from './domain/sense';

interface Snapshot {
  scenario: string;
  party: string;
  skill: string;
  rule: string;
}

const SCENARIOS = [
  { id: 'sense-b', label: 'Sense B — reject two same-issuer bills' },
  { id: 'distinct-issuers', label: 'Distinct issuers — happy path' },
  { id: 'gov-id-instant', label: 'Gov-id — instant accept' },
];

export interface AgentConsoleProps {
  /** Default scenario to stream. */
  scenario?: string;
}

/**
 * Processing-Agent Console — the agent's mind per turn: the ledger it was
 * handed, its reasoning, the `is_satisfied` verdict, and the requirements list.
 * Sense B (reject two same-issuer bills) is watchable here.
 */
export default function AgentConsole({
  scenario: initial = 'sense-b',
}: AgentConsoleProps) {
  const [scenario, setScenario] = useState(initial);
  const url = `/console/stream?scenario=${scenario}`;
  const { frames, status } = useSse<unknown>(url, ['snapshot', 'turn']);

  const snapshot = useMemo(
    () =>
      (frames.find((f) => f.event === 'snapshot')?.data as
        Snapshot | undefined) ?? null,
    [frames],
  );

  const turns = useMemo(
    () =>
      frames
        .filter((f: SseFrame<unknown>) => f.event === 'turn')
        .map((f) => mapTurn(f.data as WireTurn)),
    [frames],
  );

  return (
    <Box>
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          mb: 2,
        }}
      >
        <Typography variant="h5" component="h1">
          Processing-Agent Console
        </Typography>
        <TextField
          select
          size="small"
          label="Scenario"
          value={scenario}
          onChange={(e) => setScenario(e.target.value)}
          sx={{ minWidth: 260 }}
          slotProps={{ htmlInput: { 'aria-label': 'scenario' } }}
        >
          {SCENARIOS.map((s) => (
            <MenuItem key={s.id} value={s.id}>
              {s.label}
            </MenuItem>
          ))}
        </TextField>
      </Box>

      {snapshot && (
        <Alert severity="info" sx={{ mb: 2 }}>
          Rule: {snapshot.rule}
        </Alert>
      )}

      {turns.map((turn) => (
        <Panel
          key={turn.round}
          title={`Turn ${turn.round}`}
          action={<DoneBadge done={turn.done} />}
        >
          <Typography variant="subtitle2">Ledger handed</Typography>
          <Stack direction="row" spacing={1} sx={{ mb: 1, flexWrap: 'wrap' }}>
            {turn.ledgerHanded.map((entry) => (
              <Chip
                key={entry.id}
                size="small"
                variant="outlined"
                label={`${entry.doctype}${entry.issuer ? ` · ${entry.issuer}` : ''}`}
                color={
                  entry.disposition === 'accepted'
                    ? 'success'
                    : entry.disposition === 'rejected'
                      ? 'error'
                      : 'warning'
                }
              />
            ))}
          </Stack>

          {turn.sameIssuerReject && (
            <Alert severity="warning" sx={{ mb: 1 }}>
              Sense B: two accepted bills from the same issuer (
              {turn.acceptedIssuers.join(', ')}) — asking for one more from a
              different provider.
            </Alert>
          )}

          <Typography variant="subtitle2">Reasoning</Typography>
          <Typography variant="body2" sx={{ mb: 1 }}>
            {turn.reasoning}
          </Typography>

          <Typography variant="subtitle2">Satisfaction check</Typography>
          <Stack direction="row" spacing={1} sx={{ mb: 1, flexWrap: 'wrap' }}>
            <DispositionBadge
              disposition={turn.done ? 'accepted' : 'pending'}
            />
            {turn.acceptedIssuers.map((issuer) => (
              <Chip key={issuer} size="small" label={issuer} />
            ))}
            {!turn.done &&
              turn.outstanding.map((doctype) => (
                <Chip
                  key={doctype}
                  size="small"
                  variant="outlined"
                  label={`outstanding: ${doctype}`}
                />
              ))}
          </Stack>

          <Typography variant="subtitle2">Requirements</Typography>
          <Stack direction="row" spacing={1} sx={{ flexWrap: 'wrap' }}>
            {turn.requirements.map((req) => (
              <Chip
                key={req.item}
                size="small"
                label={req.item}
                variant="outlined"
              />
            ))}
            {turn.requirements.map((req) => (
              <RequirementBadge key={`${req.item}-s`} status={req.status} />
            ))}
          </Stack>
        </Panel>
      ))}

      {status === 'error' && (
        <Alert severity="error">Console stream error.</Alert>
      )}
    </Box>
  );
}
