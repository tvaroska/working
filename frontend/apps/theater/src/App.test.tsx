import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { theme } from '@bridge/shared';
import { describe, it, expect } from 'vitest';
import App from './App';

function renderAt(path: string) {
  return render(
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </ThemeProvider>,
  );
}

describe('App shell', () => {
  it('renders the Processing-Agent Console on /console', () => {
    renderAt('/console');
    expect(
      screen.getByRole('heading', { name: 'Processing-Agent Console' }),
    ).toBeInTheDocument();
  });

  it('shows the surface nav', () => {
    renderAt('/console');
    expect(screen.getByRole('link', { name: 'Ops' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Time-warp' })).toBeInTheDocument();
  });
});
