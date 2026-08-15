import { Box, Typography, Paper } from '@mui/material';

export default function Ops() {
  return (
    <Box sx={{ p: 3 }}>
      <Paper sx={{ p: 3 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Servicer Ops Dashboard
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Exchanges in flight, classified ledger filling live, disposition +
          HITL/escalation queues. (Sprint 1)
        </Typography>
      </Paper>
    </Box>
  );
}
