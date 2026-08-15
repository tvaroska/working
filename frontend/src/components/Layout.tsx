import { AppBar, Toolbar, Typography, Button, Box } from '@mui/material';
import { Link as RouterLink, Outlet } from 'react-router-dom';

export default function Layout() {
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      <AppBar position="static">
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            A2A Document Bridge
          </Typography>
          <Button color="inherit" component={RouterLink} to="/console">
            Console
          </Button>
          <Button color="inherit" component={RouterLink} to="/ops">
            Ops
          </Button>
          <Button color="inherit" component={RouterLink} to="/portal">
            Portal
          </Button>
        </Toolbar>
      </AppBar>
      <Box component="main" sx={{ flexGrow: 1 }}>
        <Outlet />
      </Box>
    </Box>
  );
}
