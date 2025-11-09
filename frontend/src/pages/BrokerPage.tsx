import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Tabs,
  Tab,
  Paper,
  Alert,
  Snackbar,
  Grid,
  CircularProgress,
  Button,
} from '@mui/material';
import { Refresh as RefreshIcon } from '@mui/icons-material';
import {
  BrokerConnectionCard,
  BrokerSelectionList,
  BrokerCredentialForm,
} from '../components/broker';
import type { BrokerConnection, BrokerInfo } from '../types';
import { useAppSelector } from '../store/hooks';
import { apiClient } from '../services/api';

export default function BrokerPage() {
  const { user } = useAppSelector((state) => state.auth);
  const [activeTab, setActiveTab] = useState(0);
  const [connections, setConnections] = useState<BrokerConnection[]>([]);
  const [selectedBroker, setSelectedBroker] = useState<BrokerInfo | null>(null);
  const [credentialFormOpen, setCredentialFormOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [snackbar, setSnackbar] = useState<{
    open: boolean;
    message: string;
    severity: 'success' | 'error' | 'info';
  }>({
    open: false,
    message: '',
    severity: 'info',
  });

  useEffect(() => {
    loadConnections();
  }, [user?.accountId]);

  const loadConnections = async () => {
    if (!user?.accountId) return;

    try {
      setLoading(true);
      const response = await apiClient.getBrokerConnections(user.accountId);
      setConnections(response.connections || []);
    } catch (err: any) {
      // If endpoint doesn't exist yet, just set empty array
      if (err.response?.status === 404) {
        setConnections([]);
      } else {
        console.error('Failed to load broker connections:', err);
        setSnackbar({
          open: true,
          message: 'Failed to load broker connections',
          severity: 'error',
        });
      }
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadConnections();
    setRefreshing(false);
  };

  const handleSelectBroker = (broker: BrokerInfo) => {
    setSelectedBroker(broker);
    setCredentialFormOpen(true);
  };

  const handleConnectBroker = async (brokerName: string, credentials: Record<string, string>) => {
    if (!user?.accountId) return;

    try {
      await apiClient.connectBroker(user.accountId, brokerName, credentials);
      
      setSnackbar({
        open: true,
        message: `Successfully connected to ${brokerName}`,
        severity: 'success',
      });

      // Refresh connections list
      await loadConnections();
      
      // Switch to connections tab
      setActiveTab(0);
    } catch (err: any) {
      throw err; // Re-throw to be handled by the form
    }
  };

  const handleDisconnectBroker = async (connectionId: string) => {
    try {
      await apiClient.disconnectBroker(connectionId);
      
      setSnackbar({
        open: true,
        message: 'Broker disconnected successfully',
        severity: 'success',
      });

      // Refresh connections list
      await loadConnections();
    } catch (err: any) {
      setSnackbar({
        open: true,
        message: err.response?.data?.message || 'Failed to disconnect broker',
        severity: 'error',
      });
    }
  };

  const handleCloseSnackbar = () => {
    setSnackbar({ ...snackbar, open: false });
  };

  if (!user?.accountId) {
    return (
      <Box>
        <Alert severity="error">
          Unable to load account information. Please log in again.
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" gutterBottom>
            Broker Connections
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Connect your broker accounts to enable live trading
          </Typography>
        </Box>
        <Button
          variant="outlined"
          startIcon={refreshing ? <CircularProgress size={16} /> : <RefreshIcon />}
          onClick={handleRefresh}
          disabled={refreshing}
        >
          Refresh
        </Button>
      </Box>

      <Paper sx={{ mb: 3 }}>
        <Tabs
          value={activeTab}
          onChange={(_, newValue) => setActiveTab(newValue)}
          sx={{ borderBottom: 1, borderColor: 'divider' }}
        >
          <Tab label="My Connections" />
          <Tab label="Add New Connection" />
        </Tabs>

        <Box sx={{ p: 3 }}>
          {activeTab === 0 && (
            <>
              {loading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                  <CircularProgress />
                </Box>
              ) : connections.length === 0 ? (
                <Alert severity="info" sx={{ mb: 2 }}>
                  No broker connections found. Click on "Add New Connection" tab to connect a broker.
                </Alert>
              ) : (
                <Grid container spacing={3}>
                  {connections.map((connection) => (
                    <Grid key={connection.id} size={{ xs: 12, md: 6 }}>
                      <BrokerConnectionCard
                        connection={connection}
                        onDisconnect={handleDisconnectBroker}
                      />
                    </Grid>
                  ))}
                </Grid>
              )}
            </>
          )}

          {activeTab === 1 && (
            <BrokerSelectionList onSelectBroker={handleSelectBroker} />
          )}
        </Box>
      </Paper>

      <BrokerCredentialForm
        open={credentialFormOpen}
        broker={selectedBroker}
        onClose={() => {
          setCredentialFormOpen(false);
          setSelectedBroker(null);
        }}
        onSubmit={handleConnectBroker}
      />

      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert
          onClose={handleCloseSnackbar}
          severity={snackbar.severity}
          sx={{ width: '100%' }}
        >
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
