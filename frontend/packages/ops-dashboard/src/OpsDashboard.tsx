import { useCallback, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import { Panel, DispositionBadge, FollowupBadge, useSse } from '@bridge/shared';
import {
  projectReadModel,
  type ExchangeView,
  type WireOpsSnapshot,
} from './domain/readModel';

function ExchangeCard({ exchange }: { exchange: ExchangeView }) {
  return (
    <Panel
      title={exchange.id}
      subtitle={`party: ${exchange.party}`}
      action={<FollowupBadge state={exchange.followup.state} />}
    >
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Document</TableCell>
            <TableCell>Issuer</TableCell>
            <TableCell>Disposition</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {exchange.ledger.map((entry) => (
            <TableRow key={entry.id}>
              <TableCell>{entry.doctype}</TableCell>
              <TableCell>{entry.issuer ?? '—'}</TableCell>
              <TableCell>
                <DispositionBadge disposition={entry.disposition} />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {exchange.outstanding.length > 0 && (
        <Stack direction="row" spacing={1} sx={{ mt: 1, flexWrap: 'wrap' }}>
          {exchange.outstanding.map((doctype) => (
            <Chip
              key={doctype}
              size="small"
              variant="outlined"
              label={`outstanding: ${doctype}`}
            />
          ))}
        </Stack>
      )}
    </Panel>
  );
}

/**
 * Servicer Ops Dashboard — exchanges in flight, each exchange's classified
 * ledger, disposition outcomes, and the HITL + escalation queues. Escalation
 * surfaces once the time-warp clock passes the SLA deadline.
 */
export default function OpsDashboard() {
  const [reload, setReload] = useState(0);
  const url = `/ops/stream?r=${reload}`;
  const { frames, status } = useSse<unknown>(url, ['snapshot', 'event']);

  const snapshot = useMemo(
    () =>
      (frames.find((f) => f.event === 'snapshot')?.data as
        WireOpsSnapshot | undefined) ?? null,
    [frames],
  );

  const model = useMemo(
    () => (snapshot ? projectReadModel(snapshot) : null),
    [snapshot],
  );

  const resolveHitl = useCallback(
    async (docId: string, action: 'approve' | 'reject') => {
      await fetch(`/ops/hitl/${docId}/${action}`, { method: 'POST' });
      setReload((r) => r + 1);
    },
    [],
  );

  return (
    <Box>
      <Typography variant="h5" component="h1" gutterBottom>
        Servicer Ops Dashboard
      </Typography>

      <Panel title="Escalation queue">
        {model && model.escalationQueue.length > 0 ? (
          <Stack spacing={1}>
            {model.escalationQueue.map((item) => (
              <Alert key={item.exchangeId} severity="error">
                {item.exchangeId} — {item.state} (nudges {item.nudgesFired})
              </Alert>
            ))}
          </Stack>
        ) : (
          <Typography variant="body2" color="text.secondary">
            No escalations.
          </Typography>
        )}
      </Panel>

      <Panel title="HITL queue">
        {model && model.hitlQueue.length > 0 ? (
          <Stack spacing={1}>
            {model.hitlQueue.map((item) => (
              <Box
                key={item.docId}
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1,
                  flexWrap: 'wrap',
                }}
              >
                <Typography variant="body2" sx={{ flexGrow: 1 }}>
                  {item.doctype} · {item.docId} ({item.exchangeId})
                </Typography>
                <Button
                  size="small"
                  variant="contained"
                  color="success"
                  onClick={() => resolveHitl(item.docId, 'approve')}
                >
                  Approve
                </Button>
                <Button
                  size="small"
                  variant="outlined"
                  color="error"
                  onClick={() => resolveHitl(item.docId, 'reject')}
                >
                  Reject
                </Button>
              </Box>
            ))}
          </Stack>
        ) : (
          <Typography variant="body2" color="text.secondary">
            No documents awaiting human review.
          </Typography>
        )}
      </Panel>

      <Typography variant="h6" component="h2" sx={{ mt: 2, mb: 1 }}>
        Exchanges in flight
      </Typography>
      {model?.exchanges.map((exchange) => (
        <ExchangeCard key={exchange.id} exchange={exchange} />
      ))}

      {status === 'error' && <Alert severity="error">Ops stream error.</Alert>}
    </Box>
  );
}
