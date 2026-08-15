import { Box, Typography, Paper } from '@mui/material';

export default function Portal() {
  return (
    <Box sx={{ p: 3 }}>
      <Paper sx={{ p: 3 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Provider Portal
        </Typography>
        <Typography variant="body1" color="text.secondary">
          A2UI Path-B — upload a document, see disposition + what's outstanding.
          (Sprint 1)
        </Typography>
      </Paper>
    </Box>
  );
}
