import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  Tooltip,
  CircularProgress,
  Alert,
} from '@mui/material';
import { Delete as DeleteIcon, Refresh as RefreshIcon } from '@mui/icons-material';
import { apiClient } from '../../services/api';
import type { InvestorInvitation } from '../../types';

interface PendingInvitationsListProps {
  accountId: string;
  refreshTrigger: number;
}

export default function PendingInvitationsList({ accountId, refreshTrigger }: PendingInvitationsListProps) {
  const [invitations, setInvitations] = useState<InvestorInvitation[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchInvitations = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.getAccountUsers(accountId);
      // Filter for pending invitations
      const pending = response.invitations?.filter(
        (inv: InvestorInvitation) => inv.status === 'pending'
      ) || [];
      setInvitations(pending);
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to load invitations');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInvitations();
  }, [accountId, refreshTrigger]);

  const handleRevoke = async (invitationId: string) => {
    try {
      // Note: This assumes the API has a revoke invitation endpoint
      // If not, we'll need to add it to the API client
      await apiClient.revokeInvestorAccess(accountId, invitationId);
      fetchInvitations();
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to revoke invitation');
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'warning';
      case 'accepted':
        return 'success';
      case 'rejected':
        return 'error';
      case 'expired':
        return 'default';
      default:
        return 'default';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const isExpired = (expiresAt: string) => {
    return new Date(expiresAt) < new Date();
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ mb: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">
          Pending Invitations ({invitations.length})
        </Typography>
        <Tooltip title="Refresh">
          <IconButton onClick={fetchInvitations} size="small">
            <RefreshIcon />
          </IconButton>
        </Tooltip>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {invitations.length === 0 ? (
        <Paper sx={{ p: 3, textAlign: 'center' }}>
          <Typography variant="body2" color="text.secondary">
            No pending invitations
          </Typography>
        </Paper>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Email</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Sent</TableCell>
                <TableCell>Expires</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {invitations.map((invitation) => (
                <TableRow key={invitation.id}>
                  <TableCell>{invitation.inviteeEmail}</TableCell>
                  <TableCell>
                    <Chip
                      label={isExpired(invitation.expiresAt) ? 'Expired' : invitation.status}
                      color={isExpired(invitation.expiresAt) ? 'default' : getStatusColor(invitation.status)}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>{formatDate(invitation.createdAt)}</TableCell>
                  <TableCell>
                    <Typography
                      variant="body2"
                      color={isExpired(invitation.expiresAt) ? 'error' : 'text.primary'}
                    >
                      {formatDate(invitation.expiresAt)}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">
                    <Tooltip title="Revoke Invitation">
                      <IconButton
                        onClick={() => handleRevoke(invitation.id)}
                        size="small"
                        color="error"
                      >
                        <DeleteIcon />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );
}
