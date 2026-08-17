import { createTheme } from '@mui/material/styles';

/**
 * The shared MUI theme for every Bridge surface (moved from the S0.4
 * single-app `src/theme.ts`). Keeping it in `@bridge/shared` is the
 * anti-copy-paste measure called out in `docs/features/frontend.md`.
 */
const theme = createTheme({
  palette: {
    primary: { main: '#1565c0' },
    secondary: { main: '#6a1b9a' },
  },
});

export default theme;
