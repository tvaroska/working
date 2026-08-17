import { AppBar, Toolbar, Typography, Button, Box } from '@mui/material';
import { Link as RouterLink, Outlet } from 'react-router-dom';

const NAV = [
  { to: '/theater', label: 'Theater' },
  { to: '/console', label: 'Console' },
  { to: '/ops', label: 'Ops' },
  { to: '/portal', label: 'Portal' },
  { to: '/timewarp', label: 'Time-warp' },
  { to: '/timeline', label: 'Timeline' },
];

export default function Layout() {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            A2A Document Bridge
          </Typography>
          {NAV.map((item) => (
            <Button
              key={item.to}
              color="inherit"
              component={RouterLink}
              to={item.to}
            >
              {item.label}
            </Button>
          ))}
        </Toolbar>
      </AppBar>
      <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
        <Outlet />
      </Box>
    </Box>
  );
}
