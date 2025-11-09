import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  CardActions,
  Button,
  Grid,
  CircularProgress,
  Alert,
  Chip,
} from '@mui/material';
import { Visibility as ViewIcon } from '@mui/icons-material';
import { useNavigate } from 'react-router-dom';
import { apiClient } from '../../services/api';
import type { UserAccount } from '../../types';

interface InvestorAccountsListProps {
  onAccountSelect?: (accountId: string) => void;
}

export default function InvestorAccountsList({ onAccountSelect }: InvestorAccountsListProps) {
  const [accounts, setAccounts] = useState<UserAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetchAccounts();
  }, []);

  const fetchAccounts = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.getInvestorAccounts();
      setAccounts(response.accounts || []);
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to load accounts');
    } finally {
      setLoading(false);
    }
  };

  const handleViewAccount = (accountId: string) => {
    if (onAccountSelect) {
      onAccountSelect(accountId);
    } else {
      // Navigate to dashboard with selected account
      navigate(`/dashboard?accountId=${accountId}`);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5">
          Accessible Trading Accounts
        </Typography>
        <Chip label={`${accounts.length} Account${accounts.length !== 1 ? 's' : ''}`} color="primary" />
      </Box>

      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        You have read-only access to the following trading accounts. You can view strategies, orders, positions, and analytics, but cannot modify settings or execute trades.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {accounts.length === 0 ? (
        <Card>
          <CardContent sx={{ textAlign: 'center', py: 4 }}>
            <Typography variant="body1" color="text.secondary">
              You don't have access to any trading accounts yet.
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Ask a trader to invite you to view their account.
            </Typography>
          </CardContent>
        </Card>
      ) : (
        <Grid container spacing={3}>
          {accounts.map((account) => (
            <Grid key={account.id} size={{ xs: 12, md: 6, lg: 4 }}>
              <Card>
                <CardContent>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
                    <Typography variant="h6" component="div">
                      {account.name}
                    </Typography>
                    <Chip
                      label={account.isActive ? 'Active' : 'Inactive'}
                      color={account.isActive ? 'success' : 'default'}
                      size="small"
                    />
                  </Box>
                  
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    Account ID: {account.id.substring(0, 8)}...
                  </Typography>
                  
                  <Typography variant="body2" color="text.secondary">
                    Created: {formatDate(account.createdAt)}
                  </Typography>

                  <Box sx={{ mt: 2, p: 1, bgcolor: 'info.light', borderRadius: 1 }}>
                    <Typography variant="caption" color="info.dark">
                      Read-Only Access
                    </Typography>
                  </Box>
                </CardContent>
                <CardActions>
                  <Button
                    size="small"
                    startIcon={<ViewIcon />}
                    onClick={() => handleViewAccount(account.id)}
                    fullWidth
                    variant="contained"
                  >
                    View Account
                  </Button>
                </CardActions>
              </Card>
            </Grid>
          ))}
        </Grid>
      )}
    </Box>
  );
}
