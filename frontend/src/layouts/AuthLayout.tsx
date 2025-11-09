import { Outlet } from 'react-router-dom';
import { Box, Container, Paper, Typography } from '@mui/material';

export default function AuthLayout() {
  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      }}
    >
      <Container maxWidth="sm">
        <Paper elevation={3} sx={{ p: 4 }}>
          <Typography variant="h4" align="center" gutterBottom>
            Algorithmic Trading Platform
          </Typography>
          <Typography variant="body2" align="center" color="text.secondary" sx={{ mb: 3 }}>
            Multi-user trading platform for NSE
          </Typography>
          <Outlet />
        </Paper>
      </Container>
    </Box>
  );
}
