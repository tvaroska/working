import { Box, Divider, Paper, Typography } from '@mui/material';
import { AgentConsole } from '@bridge/agent-console';
import { OpsDashboard } from '@bridge/ops-dashboard';
import { ProviderPortal } from '@bridge/provider-portal';
import { Timewarp } from '@bridge/timewarp';

/**
 * Split-Screen Theater (default): the external zone (provider portal) on the
 * left, the internal zone (processing-agent console + servicer ops) on the
 * right, with the **Gateway boundary** drawn between them. The time-warp control
 * is docked at the top. One story, both zones.
 */
export default function Theater() {
  return (
    <Box>
      <Paper variant="outlined" sx={{ p: 2, mb: 2, bgcolor: 'grey.50' }}>
        <Timewarp />
      </Paper>

      <Box
        sx={{
          display: 'flex',
          gap: 0,
          alignItems: 'stretch',
          flexDirection: { xs: 'column', md: 'row' },
        }}
      >
        {/* External zone */}
        <Box
          data-testid="external-zone"
          sx={{ flex: 1, p: 2, borderRadius: 1, bgcolor: 'secondary.50' }}
        >
          <Typography variant="overline" color="secondary">
            External zone · across the Gateway
          </Typography>
          <ProviderPortal />
        </Box>

        {/* Gateway boundary */}
        <Divider
          orientation="vertical"
          flexItem
          data-testid="gateway-boundary"
          sx={{
            borderRightWidth: 3,
            borderColor: 'warning.main',
            mx: 1,
            display: { xs: 'none', md: 'block' },
          }}
        />

        {/* Internal zone */}
        <Box
          data-testid="internal-zone"
          sx={{ flex: 1.4, p: 2, borderRadius: 1, bgcolor: 'primary.50' }}
        >
          <Typography variant="overline" color="primary">
            Internal zone · the Bridge
          </Typography>
          <AgentConsole />
          <OpsDashboard />
        </Box>
      </Box>
    </Box>
  );
}
