import { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { Panel, DispositionBadge, DoneBadge } from '@bridge/shared';
import {
  mapScreen,
  mapFulfillment,
  nextAction,
  type FulfillmentView,
  type ScreenView,
  type WireFulfillment,
  type WireScreen,
} from './domain/outstanding';

const FIXTURES = [
  'gov-id-clean',
  'bill-powerco-clean',
  'bill-aquautil-clean',
  'bill-aquautil-blurry',
  'passport-unsupported',
];

export interface ProviderPortalProps {
  context?: string;
}

/**
 * Provider Portal — the external-zone A2UI Path-B surface. Renders the
 * declarative screen from the BFF (content-not-pixels), lets the party submit a
 * fixture "upload", and shows the disposition + refreshed outstanding.
 */
export default function ProviderPortal({
  context = 'portal-demo',
}: ProviderPortalProps) {
  const [screen, setScreen] = useState<ScreenView | null>(null);
  const [fulfillment, setFulfillment] = useState<FulfillmentView | null>(null);
  const [fixtureId, setFixtureId] = useState(FIXTURES[0]);
  const [error, setError] = useState<string | null>(null);

  const loadScreen = useCallback(async () => {
    try {
      const res = await fetch(
        `/portal/screen?context=${encodeURIComponent(context)}`,
      );
      const wire = (await res.json()) as WireScreen;
      setScreen(mapScreen(wire));
    } catch {
      setError('Could not load the portal screen.');
    }
  }, [context]);

  useEffect(() => {
    void loadScreen();
  }, [loadScreen]);

  const submit = useCallback(async () => {
    setError(null);
    try {
      const res = await fetch('/portal/intake', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          context,
          mode: 'upload',
          fixture_id: fixtureId,
        }),
      });
      const body = (await res.json()) as {
        fulfillment: WireFulfillment;
        screen: WireScreen;
      };
      setFulfillment(mapFulfillment(body.fulfillment));
      setScreen(mapScreen(body.screen));
    } catch {
      setError('Intake failed.');
    }
  }, [context, fixtureId]);

  return (
    <Box>
      <Typography variant="h5" component="h1" gutterBottom>
        Provider Portal
      </Typography>

      {screen && (
        <Panel
          title="Your documents"
          action={<DoneBadge done={screen.status.done} />}
        >
          {screen.status.sent.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              Nothing submitted yet.
            </Typography>
          ) : (
            <Stack spacing={1}>
              {screen.status.sent.map((doc) => (
                <Box
                  key={doc.id}
                  sx={{ display: 'flex', alignItems: 'center', gap: 1 }}
                >
                  <Typography variant="body2" sx={{ flexGrow: 1 }}>
                    {doc.doctype}
                    {doc.issuer ? ` · ${doc.issuer}` : ''}
                    {doc.message ? ` — ${doc.message}` : ''}
                  </Typography>
                  <DispositionBadge disposition={doc.disposition} />
                </Box>
              ))}
            </Stack>
          )}
          <Alert severity="info" sx={{ mt: 2 }}>
            Next: {nextAction(screen)}
          </Alert>
        </Panel>
      )}

      {screen?.intake && (
        <Panel title="Upload a document" subtitle={screen.intake.prompt}>
          <Stack
            direction="row"
            spacing={1}
            sx={{ alignItems: 'center', flexWrap: 'wrap' }}
          >
            <TextField
              select
              size="small"
              label="Fixture"
              value={fixtureId}
              onChange={(e) => setFixtureId(e.target.value)}
              sx={{ minWidth: 240 }}
              slotProps={{ htmlInput: { 'aria-label': 'fixture' } }}
            >
              {FIXTURES.map((id) => (
                <MenuItem key={id} value={id}>
                  {id}
                </MenuItem>
              ))}
            </TextField>
            <Button variant="contained" onClick={submit}>
              Submit
            </Button>
          </Stack>
        </Panel>
      )}

      {fulfillment && (
        <Panel title="Last submission">
          <Stack
            direction="row"
            spacing={1}
            sx={{ alignItems: 'center', flexWrap: 'wrap' }}
          >
            <Chip size="small" label={`phase: ${fulfillment.phase}`} />
            {fulfillment.disposition && (
              <DispositionBadge disposition={fulfillment.disposition} />
            )}
            {fulfillment.awaitingResubmission && (
              <Chip size="small" color="warning" label="resubmit requested" />
            )}
          </Stack>
        </Panel>
      )}

      {error && <Alert severity="error">{error}</Alert>}
    </Box>
  );
}
