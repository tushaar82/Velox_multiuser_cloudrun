import { useState } from 'react';
import {
  Box,
  Button,
  TextField,
  Typography,
  Alert,
  CircularProgress,
} from '@mui/material';
import { apiClient } from '../../services/api';

interface InviteInvestorFormProps {
  accountId: string;
  onInviteSent: () => void;
}

export default function InviteInvestorForm({ accountId, onInviteSent }: InviteInvestorFormProps) {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(false);

    if (!email || !email.includes('@')) {
      setError('Please enter a valid email address');
      return;
    }

    setLoading(true);
    try {
      await apiClient.inviteInvestor(accountId, email);
      setSuccess(true);
      setEmail('');
      onInviteSent();
      
      // Clear success message after 3 seconds
      setTimeout(() => setSuccess(false), 3000);
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to send invitation');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box component="form" onSubmit={handleSubmit} sx={{ mb: 3 }}>
      <Typography variant="h6" gutterBottom>
        Invite Investor
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Invite an investor to view your trading account. They will receive an email with a link to accept the invitation.
        Invitations expire after 7 days.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 2 }}>
          Invitation sent successfully!
        </Alert>
      )}

      <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start' }}>
        <TextField
          label="Investor Email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="investor@example.com"
          fullWidth
          required
          disabled={loading}
        />
        <Button
          type="submit"
          variant="contained"
          disabled={loading || !email}
          sx={{ minWidth: 120, height: 56 }}
        >
          {loading ? <CircularProgress size={24} /> : 'Send Invite'}
        </Button>
      </Box>
    </Box>
  );
}
