import { Box, Typography, Paper } from '@mui/material';

export default function Console() {
  return (
    <Box sx={{ p: 3 }}>
      <Paper sx={{ p: 3 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Processing-Agent Console
        </Typography>
        <Typography variant="body1" color="text.secondary">
          The counterparty agent's mind — ledger, reasoning, satisfaction check,
          requirements list. (Sprint 1)
        </Typography>
      </Paper>
    </Box>
  );
}
