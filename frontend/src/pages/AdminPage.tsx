import { useState } from 'react';
import { Box, Typography, Tabs, Tab, Paper } from '@mui/material';
import { StrategyLimitAdminControl } from '../components/strategy';
import {
  SymbolMappingManager,
  SystemHealthOverview,
  UserManagementTable,
  TradingActivityCharts,
  AuditLogViewer,
  DailyReportGenerator,
} from '../components/admin';

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
          variant="scrollable"
          scrollButtons="auto"
        >
          <Tab label="System Health" />
          <Tab label="User Management" />
          <Tab label="Trading Activity" />
          <Tab label="Audit Logs" />
          <Tab label="Daily Reports" />
          <Tab label="Strategy Limits" />
          <Tab label="Symbol Mappings" />
        </Tabs>

        <Box sx={{ p: 3 }}>
          {activeTab === 0 && <SystemHealthOverview />}

          {activeTab === 1 && <UserManagementTable />}

          {activeTab === 2 && <TradingActivityCharts />}

          {activeTab === 3 && <AuditLogViewer />}

          {activeTab === 4 && <DailyReportGenerator />}

          {activeTab === 5 && <StrategyLimitAdminControl />}

          {activeTab === 6 && <SymbolMappingManager />}
        </Box>
      </Paper>
    </Box>
  );
}
