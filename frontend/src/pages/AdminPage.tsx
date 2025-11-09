import { useState } from 'react';
import { Box, Typography, Tabs, Tab, Paper } from '@mui/material';
import { StrategyLimitAdminControl } from '../components/strategy';
import { SymbolMappingManager } from '../components/admin';

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState(0);

  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Admin Dashboard
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        System administration and configuration
      </Typography>

      <Paper sx={{ mb: 3 }}>
        <Tabs
          value={activeTab}
          onChange={(_, newValue) => setActiveTab(newValue)}
          sx={{ borderBottom: 1, borderColor: 'divider' }}
        >
          <Tab label="Strategy Limits" />
          <Tab label="Symbol Mappings" />
          <Tab label="System Health" />
          <Tab label="User Management" />
          <Tab label="Audit Logs" />
        </Tabs>

        <Box sx={{ p: 3 }}>
          {activeTab === 0 && <StrategyLimitAdminControl />}

          {activeTab === 1 && <SymbolMappingManager />}

          {activeTab === 2 && (
            <Typography variant="body1" color="text.secondary">
              System health monitoring will be implemented in subtask 16.13
            </Typography>
          )}

          {activeTab === 3 && (
            <Typography variant="body1" color="text.secondary">
              User management will be implemented in subtask 16.13
            </Typography>
          )}

          {activeTab === 4 && (
            <Typography variant="body1" color="text.secondary">
              Audit logs will be implemented in subtask 16.13
            </Typography>
          )}
        </Box>
      </Paper>
    </Box>
  );
}
