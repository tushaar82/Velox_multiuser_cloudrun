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
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions,
  Button,
} from '@mui/material';
import { PersonRemove as RemoveIcon, Refresh as RefreshIcon } from '@mui/icons-material';
import { apiClient } from '../../services/api';
import { UserRole } from '../../types';

interface AccountUser {
  id: string;
  email: string;
  role: UserRole;
  grantedAt: string;
}

interface AccountUsersListProps {
  accountId: string;
  currentUserId: string;
  refreshTrigger: number;
}

export default function AccountUsersList({ accountId, currentUserId, refreshTrigger }: AccountUsersListProps) {
  const [users, setUsers] = useState<AccountUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [revokeDialogOpen, setRevokeDialogOpen] = useState(false);
  const [selectedUser, setSelectedUser] = useState<AccountUser | null>(null);

  const fetchUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.getAccountUsers(accountId);
      setUsers(response.users || []);
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to load users');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, [accountId, refreshTrigger]);

  const handleRevokeClick = (user: AccountUser) => {
    setSelectedUser(user);
    setRevokeDialogOpen(true);
  };

  const handleRevokeConfirm = async () => {
    if (!selectedUser) return;

    try {
      await apiClient.revokeInvestorAccess(accountId, selectedUser.id);
      setRevokeDialogOpen(false);
      setSelectedUser(null);
      fetchUsers();
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to revoke access');
      setRevokeDialogOpen(false);
    }
  };

  const getRoleColor = (role: UserRole) => {
    switch (role) {
      case UserRole.TRADER:
        return 'primary';
      case UserRole.INVESTOR:
        return 'secondary';
      case UserRole.ADMIN:
        return 'error';
      default:
        return 'default';
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
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">
          Account Users ({users.length})
        </Typography>
        <Tooltip title="Refresh">
          <IconButton onClick={fetchUsers} size="small">
            <RefreshIcon />
          </IconButton>
        </Tooltip>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {users.length === 0 ? (
        <Paper sx={{ p: 3, textAlign: 'center' }}>
          <Typography variant="body2" color="text.secondary">
            No users found
          </Typography>
        </Paper>
      ) : (
        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>Email</TableCell>
                <TableCell>Role</TableCell>
                <TableCell>Access Granted</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {users.map((user) => (
                <TableRow key={user.id}>
                  <TableCell>
                    {user.email}
                    {user.id === currentUserId && (
                      <Chip label="You" size="small" sx={{ ml: 1 }} />
                    )}
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={user.role}
                      color={getRoleColor(user.role)}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>{formatDate(user.grantedAt)}</TableCell>
                  <TableCell align="right">
                    {user.role === UserRole.INVESTOR && user.id !== currentUserId && (
                      <Tooltip title="Revoke Access">
                        <IconButton
                          onClick={() => handleRevokeClick(user)}
                          size="small"
                          color="error"
                        >
                          <RemoveIcon />
                        </IconButton>
                      </Tooltip>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Revoke Confirmation Dialog */}
      <Dialog open={revokeDialogOpen} onClose={() => setRevokeDialogOpen(false)}>
        <DialogTitle>Revoke Investor Access</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Are you sure you want to revoke access for {selectedUser?.email}? They will no longer be able to view this account's trading activity.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRevokeDialogOpen(false)}>Cancel</Button>
          <Button onClick={handleRevokeConfirm} color="error" variant="contained">
            Revoke Access
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
