import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import theme from './theme';
import App from './App';
import { describe, it, expect } from 'vitest';

describe('App', () => {
  it('renders Processing-Agent Console when navigating to /console', () => {
    render(
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <MemoryRouter initialEntries={['/console']}>
          <App />
        </MemoryRouter>
      </ThemeProvider>,
    );

    expect(screen.getByText('Processing-Agent Console')).toBeInTheDocument();
  });
});
