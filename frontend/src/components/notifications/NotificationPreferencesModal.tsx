import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  FormGroup,
  FormControlLabel,
  Checkbox,
  Typography,
  Box,
  Alert,
  CircularProgress,
  Divider,
} from '@mui/material';
import { useAppSelector } from '../../store/hooks';
import { apiClient } from '../../services/api';
import type { NotificationPreferences } from '../../types';

interface NotificationPreferencesModalProps {
  open: boolean;
  onClose: () => void;
}

const notificationTypes = [
  { key: 'order_executed', label: 'Order Executed', description: 'Notifications when orders are filled' },
  { key: 'strategy_error', label: 'Strategy Error', description: 'Alerts when strategies encounter errors' },
  { key: 'threshold_alert', label: 'Threshold Alert', description: 'Alerts when P&L reaches configured thresholds' },
  { key: 'connection_lost', label: 'Connection Lost', description: 'Alerts when broker or market data connection drops' },
  { key: 'trailing_stop_triggered', label: 'Trailing Stop Triggered', description: 'Notifications when trailing stop-loss executes' },
  { key: 'investor_invitation', label: 'Investor Invitation', description: 'Notifications about investor invitations' },
  { key: 'session_timeout_warning', label: 'Session Timeout Warning', description: 'Warning before automatic logout' },
  { key: 'account_locked', label: 'Account Locked', description: 'Notification when account is locked' },
  { key: 'system_alert', label: 'System Alert', description: 'Important system notifications' },
];

const channels = [
  { key: 'in_app', label: 'In-App' },
  { key: 'email', label: 'Email' },
  { key: 'sms', label: 'SMS' },
];

export default function NotificationPreferencesModal({ open, onClose }: NotificationPreferencesModalProps) {
  const { user } = useAppSelector((state) => state.auth);
  const [preferences, setPreferences] = useState<NotificationPreferences | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    if (open && user?.id) {
      loadPreferences();
    }
  }, [open, user?.id]);

  const loadPreferences = async () => {
    if (!user?.id) return;

    setLoading(true);
    setError(null);
    try {
      const data = await apiClient.getNotificationPreferences(user.id);
      setPreferences(data);
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to load preferences');
      // Initialize with default preferences if none exist
      const defaultPreferences: NotificationPreferences = {
        userId: user.id,
        preferences: {},
      };
      notificationTypes.forEach((type) => {
        defaultPreferences.preferences[type.key] = {
          enabled: true,
          channels: ['in_app'],
        };
      });
      setPreferences(defaultPreferences);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleEnabled = (notificationType: string) => {
    if (!preferences) return;

    setPreferences({
      ...preferences,
      preferences: {
        ...preferences.preferences,
        [notificationType]: {
          ...preferences.preferences[notificationType],
          enabled: !preferences.preferences[notificationType]?.enabled,
        },
      },
    });
  };

  const handleToggleChannel = (notificationType: string, channel: string) => {
    if (!preferences) return;

    const currentChannels = preferences.preferences[notificationType]?.channels || [];
    const newChannels = currentChannels.includes(channel as any)
      ? currentChannels.filter((c) => c !== channel)
      : [...currentChannels, channel as any];

    setPreferences({
      ...preferences,
      preferences: {
        ...preferences.preferences,
        [notificationType]: {
          ...preferences.preferences[notificationType],
          enabled: preferences.preferences[notificationType]?.enabled ?? true,
          channels: newChannels,
        },
      },
    });
  };

  const handleSave = async () => {
    if (!user?.id || !preferences) return;

    setSaving(true);
    setError(null);
    setSuccess(false);
    try {
      await apiClient.updateNotificationPreferences(user.id, preferences);
      setSuccess(true);
      setTimeout(() => {
        onClose();
      }, 1500);
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to save preferences');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Notification Preferences</DialogTitle>
      <DialogContent>
        {loading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
            <CircularProgress />
          </Box>
        )}

        {error && !loading && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {success && (
          <Alert severity="success" sx={{ mb: 2 }}>
            Preferences saved successfully!
          </Alert>
        )}

        {!loading && preferences && (
          <Box>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              Configure how you want to receive notifications for different events.
            </Typography>

            {notificationTypes.map((type) => {
              const config = preferences.preferences[type.key] || { enabled: true, channels: ['in_app'] };
              return (
                <Box key={type.key} sx={{ mb: 3 }}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={config.enabled}
                        onChange={() => handleToggleEnabled(type.key)}
                      />
                    }
                    label={
                      <Box>
                        <Typography variant="body1" fontWeight="medium">
                          {type.label}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {type.description}
                        </Typography>
                      </Box>
                    }
                  />
                  {config.enabled && (
                    <Box sx={{ ml: 4, mt: 1 }}>
                      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                        Channels:
                      </Typography>
                      <FormGroup row>
                        {channels.map((channel) => (
                          <FormControlLabel
                            key={channel.key}
                            control={
                              <Checkbox
                                size="small"
                                checked={config.channels.includes(channel.key as any)}
                                onChange={() => handleToggleChannel(type.key, channel.key)}
                              />
                            }
                            label={channel.label}
                          />
                        ))}
                      </FormGroup>
                    </Box>
                  )}
                  <Divider sx={{ mt: 2 }} />
                </Box>
              );
            })}
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={saving}>
          Cancel
        </Button>
        <Button onClick={handleSave} variant="contained" disabled={saving || loading}>
          {saving ? <CircularProgress size={24} /> : 'Save Preferences'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
