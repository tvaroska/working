import type { ReactNode } from 'react';
import { Box, Paper, Typography } from '@mui/material';

export interface PanelProps {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  children?: ReactNode;
}

/**
 * A titled surface card used across the surfaces (console turns, ops queues,
 * portal screen). Content-not-pixels: surfaces pass content, not layout.
 */
export default function Panel({
  title,
  subtitle,
  action,
  children,
}: PanelProps) {
  return (
    <Paper variant="outlined" sx={{ p: 2, mb: 2 }}>
      <Box
        sx={{
          display: 'flex',
          alignItems: 'baseline',
          justifyContent: 'space-between',
          gap: 1,
          mb: subtitle || children ? 1 : 0,
        }}
      >
        <Typography variant="h6" component="h2">
          {title}
        </Typography>
        {action}
      </Box>
      {subtitle && (
        <Typography variant="body2" color="text.secondary" gutterBottom>
          {subtitle}
        </Typography>
      )}
      {children}
    </Paper>
  );
}
