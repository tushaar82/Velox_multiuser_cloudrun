import { useState } from 'react';
import { Box, Typography, Tabs, Tab, Paper, Divider } from '@mui/material';
import { useAppSelector } from '../store/hooks';
import { UserRole } from '../types';
import {
  InviteInvestorForm,
  PendingInvitationsList,
  AccountUsersList,
  InvestorAccountsList,
  ReadOnlyIndicator,
} from '../components/investor';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`investor-tabpanel-${index}`}
      aria-labelledby={`investor-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

export default function InvestorPage() {
  const { user } = useAppSelector((state) => state.auth);
  const [tabValue, setTabValue] = useState(0);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
  };

  const handleInviteSent = () => {
    setRefreshTrigger((prev) => prev + 1);
  };

  // If user is an investor, show only the accounts they can access
  if (user?.role === UserRole.INVESTOR) {
    return (
      <Box>
        <Typography variant="h4" gutterBottom>
          My Investment Accounts
        </Typography>
        <ReadOnlyIndicator />
        <InvestorAccountsList />
      </Box>
    );
  }

  // For traders and admins, show the full management interface
  return (
    <Box>
      <Typography variant="h4" gutterBottom>
        Investor Management
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Manage investor access to your trading account. Investors can view your strategies, orders, positions, and analytics in read-only mode.
      </Typography>

      <Paper sx={{ mb: 3 }}>
        <Tabs
          value={tabValue}
          onChange={handleTabChange}
          aria-label="investor management tabs"
          sx={{ borderBottom: 1, borderColor: 'divider' }}
        >
          <Tab label="Invite Investors" />
          <Tab label="Pending Invitations" />
          <Tab label="Account Users" />
        </Tabs>

        <Box sx={{ p: 3 }}>
          <TabPanel value={tabValue} index={0}>
            <InviteInvestorForm
              accountId={user?.accountId || ''}
              onInviteSent={handleInviteSent}
            />
            <Divider sx={{ my: 3 }} />
            <Typography variant="body2" color="text.secondary">
              <strong>Note:</strong> Invited investors will receive an email with a link to accept the invitation.
              Invitations expire after 7 days. Investors will have read-only access and cannot modify strategies or execute trades.
            </Typography>
          </TabPanel>

          <TabPanel value={tabValue} index={1}>
            <PendingInvitationsList
              accountId={user?.accountId || ''}
              refreshTrigger={refreshTrigger}
            />
          </TabPanel>

          <TabPanel value={tabValue} index={2}>
            <AccountUsersList
              accountId={user?.accountId || ''}
              currentUserId={user?.id || ''}
              refreshTrigger={refreshTrigger}
            />
          </TabPanel>
        </Box>
      </Paper>
    </Box>
  );
}
