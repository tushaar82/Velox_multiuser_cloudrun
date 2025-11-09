import { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  Box,
  Alert,
  CircularProgress,
  Typography,
  IconButton,
  InputAdornment,
} from '@mui/material';
import {
  Visibility as VisibilityIcon,
  VisibilityOff as VisibilityOffIcon,
  Lock as LockIcon,
} from '@mui/icons-material';
import type { BrokerInfo } from '../../types';

interface BrokerCredentialFormProps {
  open: boolean;
  broker: BrokerInfo | null;
  onClose: () => void;
  onSubmit: (brokerName: string, credentials: Record<string, string>) => Promise<void>;
}

export default function BrokerCredentialForm({
  open,
  broker,
  onClose,
  onSubmit,
}: BrokerCredentialFormProps) {
  const [credentials, setCredentials] = useState<Record<string, string>>({});
  const [showPassword, setShowPassword] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleChange = (fieldName: string, value: string) => {
    setCredentials((prev) => ({
      ...prev,
      [fieldName]: value,
    }));
  };

  const toggleShowPassword = (fieldName: string) => {
    setShowPassword((prev) => ({
      ...prev,
      [fieldName]: !prev[fieldName],
    }));
  };

  const handleSubmit = async () => {
    if (!broker) return;

    // Validate all required fields are filled
    const missingFields = broker.credentialsRequired.filter(
      (field) => !credentials[field.name] || credentials[field.name].trim() === ''
    );

    if (missingFields.length > 0) {
      setError(`Please fill in all required fields: ${missingFields.map(f => f.name).join(', ')}`);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      await onSubmit(broker.name, credentials);
      // Reset form on success
      setCredentials({});
      setShowPassword({});
      onClose();
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to connect broker. Please check your credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    if (!loading) {
      setCredentials({});
      setShowPassword({});
      setError(null);
      onClose();
    }
  };

  if (!broker) return null;

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        Connect to {broker.name}
      </DialogTitle>
      <DialogContent>
        <Alert severity="info" icon={<LockIcon />} sx={{ mb: 3, mt: 1 }}>
          <Typography variant="body2">
            <strong>Security Notice:</strong> Your credentials will be encrypted using AES-256 encryption before storage.
            We never store your credentials in plain text.
          </Typography>
        </Alert>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {broker.credentialsRequired.map((field) => {
            const isPasswordField = field.type === 'password' || 
                                   field.name.toLowerCase().includes('password') ||
                                   field.name.toLowerCase().includes('secret') ||
                                   field.name.toLowerCase().includes('key');
            
            return (
              <TextField
                key={field.name}
                label={field.name}
                type={isPasswordField && !showPassword[field.name] ? 'password' : 'text'}
                value={credentials[field.name] || ''}
                onChange={(e) => handleChange(field.name, e.target.value)}
                helperText={field.description}
                required
                fullWidth
                disabled={loading}
                InputProps={isPasswordField ? {
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        onClick={() => toggleShowPassword(field.name)}
                        edge="end"
                        disabled={loading}
                      >
                        {showPassword[field.name] ? <VisibilityOffIcon /> : <VisibilityIcon />}
                      </IconButton>
                    </InputAdornment>
                  ),
                } : undefined}
              />
            );
          })}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose} disabled={loading}>
          Cancel
        </Button>
        <Button
          onClick={handleSubmit}
          variant="contained"
          disabled={loading}
          startIcon={loading ? <CircularProgress size={16} /> : null}
        >
          {loading ? 'Connecting...' : 'Connect'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
