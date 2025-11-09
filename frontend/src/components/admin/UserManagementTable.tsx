import { useEffect, useState } from 'react';
import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  Button,
  Chip,
  CircularProgress,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  TextField,
  InputAdornment,
  IconButton,
  Tooltip,
} from '@mui/material';
import {
  Block as BlockIcon,
  CheckCircle as CheckCircleIcon,
  Search as SearchIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { apiClient } from '../../services/api';

interface UserAccount {
  account_id: string;
  account_name: string;
  trader_email: string;
  trader_id: string;
  is_active: boolean;
  active_strategies: number;
  total_orders: number;
  last_activity: string;
}

export function UserManagementTable() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [accounts, setAccounts] = useState<UserAccount[]>([]);
  const [filteredAccounts, setFilteredAccounts] = useState<UserAccount[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [includeInactive, setIncludeInactive] = useState(false);
  const [confirmDialog, setConfirmDialog] = useState<{
    open: boolean;
    userId: string;
    action: 'enable' | 'disable';
    email: string;
  }>({ open: false, userId: '', action: 'disable', email: '' });

  const fetchAccounts = async () => {
    try {
      setError(null);
      setLoading(true);
      const response = await apiClient.client.get('/api/admin/accounts', {
        params: { include_inactive: includeInactive },
      });
      setAccounts(response.data.accounts);
      setFilteredAccounts(response.data.accounts);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to fetch user accounts');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAccounts();
  }, [includeInactive]);

  useEffect(() => {
    if (searchQuery.trim() === '') {
      setFilteredAccounts(accounts);
    } else {
      const query = searchQuery.toLowerCase();
      setFilteredAccounts(
        accounts.filter(
          (account) =>
            account.account_name.toLowerCase().includes(query) ||
            account.trader_email.toLowerCase().includes(query) ||
            account.account_id.toLowerCase().includes(query)
        )
      );
    }
  }, [searchQuery, accounts]);

  const handleDisableUser = async (userId: string) => {
    try {
      await apiClient.disableUser(userId);
      await fetchAccounts();
      setConfirmDialog({ open: false, userId: '', action: 'disable', email: '' });
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to disable user');
    }
  };

  const handleEnableUser = async (userId: string) => {
    try {
      await apiClient.enableUser(userId);
      await fetchAccounts();
      setConfirmDialog({ open: false, userId: '', action: 'enable', email: '' });
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to enable user');
    }
  };

  const openConfirmDialog = (userId: string, action: 'enable' | 'disable', email: string) => {
    setConfirmDialog({ open: true, userId, action, email });
  };

  const closeConfirmDialog = () => {
    setConfirmDialog({ open: false, userId: '', action: 'disable', email: '' });
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight={400}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Typography variant="h6">User Account Management</Typography>
        <Box display="flex" gap={2}>
          <Button
            variant="outlined"
            size="small"
            onClick={() => setIncludeInactive(!includeInactive)}
          >
            {includeInactive ? 'Hide Inactive' : 'Show Inactive'}
          </Button>
          <Tooltip title="Refresh">
            <IconButton onClick={fetchAccounts} size="small">
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      <TextField
        fullWidth
        placeholder="Search by account name, email, or ID..."
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        sx={{ mb: 2 }}
        InputProps={{
          startAdornment: (
            <InputAdornment position="start">
              <SearchIcon />
            </InputAdornment>
          ),
        }}
      />

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Account Name</TableCell>
              <TableCell>Trader Email</TableCell>
              <TableCell align="center">Status</TableCell>
              <TableCell align="center">Active Strategies</TableCell>
              <TableCell align="center">Total Orders</TableCell>
              <TableCell>Last Activity</TableCell>
              <TableCell align="center">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredAccounts.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  <Typography variant="body2" color="text.secondary" py={4}>
                    {searchQuery ? 'No accounts match your search' : 'No accounts found'}
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              filteredAccounts.map((account) => (
                <TableRow key={account.account_id} hover>
                  <TableCell>
                    <Typography variant="body2" fontWeight="medium">
                      {account.account_name}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {account.account_id}
                    </Typography>
                  </TableCell>
                  <TableCell>{account.trader_email}</TableCell>
                  <TableCell align="center">
                    <Chip
                      label={account.is_active ? 'Active' : 'Disabled'}
                      color={account.is_active ? 'success' : 'default'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell align="center">
                    <Chip label={account.active_strategies} size="small" color="primary" />
                  </TableCell>
                  <TableCell align="center">{account.total_orders}</TableCell>
                  <TableCell>
                    <Typography variant="body2">
                      {account.last_activity
                        ? new Date(account.last_activity).toLocaleString()
                        : 'Never'}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    {account.is_active ? (
                      <Button
                        variant="outlined"
                        color="error"
                        size="small"
                        startIcon={<BlockIcon />}
                        onClick={() =>
                          openConfirmDialog(account.trader_id, 'disable', account.trader_email)
                        }
                      >
                        Disable
                      </Button>
                    ) : (
                      <Button
                        variant="outlined"
                        color="success"
                        size="small"
                        startIcon={<CheckCircleIcon />}
                        onClick={() =>
                          openConfirmDialog(account.trader_id, 'enable', account.trader_email)
                        }
                      >
                        Enable
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* Confirmation Dialog */}
      <Dialog open={confirmDialog.open} onClose={closeConfirmDialog}>
        <DialogTitle>
          {confirmDialog.action === 'disable' ? 'Disable User Account' : 'Enable User Account'}
        </DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to {confirmDialog.action} the account for{' '}
            <strong>{confirmDialog.email}</strong>?
            {confirmDialog.action === 'disable' && (
              <>
                <br />
                <br />
                This will immediately terminate all active sessions and pause all running strategies
                for this user.
              </>
            )}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={closeConfirmDialog}>Cancel</Button>
          <Button
            onClick={() =>
              confirmDialog.action === 'disable'
                ? handleDisableUser(confirmDialog.userId)
                : handleEnableUser(confirmDialog.userId)
            }
            color={confirmDialog.action === 'disable' ? 'error' : 'success'}
            variant="contained"
          >
            {confirmDialog.action === 'disable' ? 'Disable' : 'Enable'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
