import { useEffect, useState } from 'react';
import {
  Box,
  Paper,
  List,
  ListItem,
  ListItemText,
  Typography,
  IconButton,
  Chip,
  CircularProgress,
  Alert,
  Button,
  TextField,
  MenuItem,
  Stack,
} from '@mui/material';
import { CheckCircle, Error as ErrorIcon, Warning, Info, Settings } from '@mui/icons-material';
import { useAppDispatch, useAppSelector } from '../../store/hooks';
import { fetchNotifications, markNotificationRead } from '../../store/slices/notificationSlice';
import type { Notification } from '../../types';
import { format } from 'date-fns';
import NotificationPreferencesModal from './NotificationPreferencesModal';

export default function NotificationHistory() {
  const dispatch = useAppDispatch();
  const { user } = useAppSelector((state) => state.auth);
  const { notifications, loading, error } = useAppSelector((state) => state.notification);
  const [filterSeverity, setFilterSeverity] = useState<string>('all');
  const [filterRead, setFilterRead] = useState<string>('all');
  const [preferencesOpen, setPreferencesOpen] = useState(false);

  useEffect(() => {
    if (user?.id) {
      dispatch(fetchNotifications(user.id));
    }
  }, [dispatch, user?.id]);

  const handleMarkAsRead = async (notificationId: string) => {
    await dispatch(markNotificationRead(notificationId));
  };

  const handleMarkAllAsRead = async () => {
    const unreadNotifications = notifications.filter((n) => !n.readAt);
    for (const notification of unreadNotifications) {
      await dispatch(markNotificationRead(notification.id));
    }
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'error':
        return <ErrorIcon color="error" />;
      case 'warning':
        return <Warning color="warning" />;
      case 'info':
        return <Info color="info" />;
      default:
        return <CheckCircle color="success" />;
    }
  };

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'error':
        return 'error';
      case 'warning':
        return 'warning';
      case 'info':
        return 'info';
      default:
        return 'success';
    }
  };

  const filteredNotifications = notifications.filter((notification) => {
    if (filterSeverity !== 'all' && notification.severity !== filterSeverity) {
      return false;
    }
    if (filterRead === 'unread' && notification.readAt) {
      return false;
    }
    if (filterRead === 'read' && !notification.readAt) {
      return false;
    }
    return true;
  });

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h4">Notification History</Typography>
        <Button
          variant="outlined"
          startIcon={<Settings />}
          onClick={() => setPreferencesOpen(true)}
        >
          Preferences
        </Button>
      </Box>

      <Paper sx={{ p: 2, mb: 3 }}>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems="stretch">
          <TextField
            select
            fullWidth
            label="Filter by Severity"
            value={filterSeverity}
            onChange={(e) => setFilterSeverity(e.target.value)}
            size="small"
          >
            <MenuItem value="all">All Severities</MenuItem>
            <MenuItem value="error">Error</MenuItem>
            <MenuItem value="warning">Warning</MenuItem>
            <MenuItem value="info">Info</MenuItem>
          </TextField>
          <TextField
            select
            fullWidth
            label="Filter by Status"
            value={filterRead}
            onChange={(e) => setFilterRead(e.target.value)}
            size="small"
          >
            <MenuItem value="all">All</MenuItem>
            <MenuItem value="unread">Unread</MenuItem>
            <MenuItem value="read">Read</MenuItem>
          </TextField>
          <Button
            fullWidth
            variant="contained"
            onClick={handleMarkAllAsRead}
            disabled={notifications.filter((n) => !n.readAt).length === 0}
          >
            Mark All as Read
          </Button>
        </Stack>
      </Paper>

      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
          <CircularProgress />
        </Box>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      {!loading && !error && filteredNotifications.length === 0 && (
        <Paper sx={{ p: 3, textAlign: 'center' }}>
          <Typography variant="body1" color="text.secondary">
            No notifications found
          </Typography>
        </Paper>
      )}

      {!loading && !error && filteredNotifications.length > 0 && (
        <Paper>
          <List>
            {filteredNotifications.map((notification: Notification, index: number) => (
              <ListItem
                key={notification.id}
                sx={{
                  bgcolor: notification.readAt ? 'transparent' : 'action.hover',
                  borderBottom: index < filteredNotifications.length - 1 ? '1px solid' : 'none',
                  borderColor: 'divider',
                }}
                secondaryAction={
                  !notification.readAt && (
                    <IconButton
                      edge="end"
                      onClick={() => handleMarkAsRead(notification.id)}
                      title="Mark as read"
                    >
                      <CheckCircle />
                    </IconButton>
                  )
                }
              >
                <Box sx={{ display: 'flex', gap: 2, width: '100%', pr: 6 }}>
                  <Box sx={{ mt: 1 }}>{getSeverityIcon(notification.severity)}</Box>
                  <Box sx={{ flex: 1 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                      <Typography
                        variant="body1"
                        fontWeight={notification.readAt ? 'normal' : 'bold'}
                      >
                        {notification.title}
                      </Typography>
                      <Chip
                        label={notification.severity}
                        size="small"
                        color={getSeverityColor(notification.severity) as any}
                      />
                      {!notification.readAt && (
                        <Chip label="Unread" size="small" color="primary" />
                      )}
                    </Box>
                    <ListItemText
                      primary={
                        <Typography variant="body2" color="text.secondary">
                          {notification.message}
                        </Typography>
                      }
                      secondary={
                        <Box sx={{ display: 'flex', gap: 2, mt: 1 }}>
                          <Typography variant="caption" color="text.secondary">
                            Type: {notification.type}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {format(new Date(notification.createdAt), 'PPpp')}
                          </Typography>
                          {notification.readAt && (
                            <Typography variant="caption" color="text.secondary">
                              Read: {format(new Date(notification.readAt), 'PPpp')}
                            </Typography>
                          )}
                        </Box>
                      }
                    />
                  </Box>
                </Box>
              </ListItem>
            ))}
          </List>
        </Paper>
      )}

      <NotificationPreferencesModal
        open={preferencesOpen}
        onClose={() => setPreferencesOpen(false)}
      />
    </Box>
  );
}
