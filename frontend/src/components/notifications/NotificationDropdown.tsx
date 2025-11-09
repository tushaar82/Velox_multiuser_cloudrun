import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  List,
  ListItem,
  ListItemText,
  Typography,
  Button,
  Divider,
  IconButton,
  CircularProgress,
  Alert,
} from '@mui/material';
import { Close, CheckCircle, Warning, Error as ErrorIcon, Info } from '@mui/icons-material';
import { useAppDispatch, useAppSelector } from '../../store/hooks';
import { fetchNotifications, markNotificationRead } from '../../store/slices/notificationSlice';
import type { Notification } from '../../types';
import { formatDistanceToNow } from 'date-fns';

interface NotificationDropdownProps {
  onClose: () => void;
}

export default function NotificationDropdown({ onClose }: NotificationDropdownProps) {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const { user } = useAppSelector((state) => state.auth);
  const { notifications, loading, error } = useAppSelector((state) => state.notification);

  useEffect(() => {
    if (user?.id) {
      dispatch(fetchNotifications(user.id));
    }
  }, [dispatch, user?.id]);

  const handleMarkAsRead = async (notificationId: string, event: React.MouseEvent) => {
    event.stopPropagation();
    await dispatch(markNotificationRead(notificationId));
  };

  const handleViewAll = () => {
    onClose();
    navigate('/notifications');
  };

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'error':
        return <ErrorIcon color="error" fontSize="small" />;
      case 'warning':
        return <Warning color="warning" fontSize="small" />;
      case 'info':
        return <Info color="info" fontSize="small" />;
      default:
        return <CheckCircle color="success" fontSize="small" />;
    }
  };

  const recentNotifications = notifications.slice(0, 5);

  return (
    <Box sx={{ width: 400, maxHeight: 500 }}>
      <Box sx={{ p: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h6">Notifications</Typography>
        <IconButton size="small" onClick={onClose}>
          <Close />
        </IconButton>
      </Box>
      <Divider />

      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
          <CircularProgress />
        </Box>
      )}

      {error && (
        <Box sx={{ p: 2 }}>
          <Alert severity="error">{error}</Alert>
        </Box>
      )}

      {!loading && !error && recentNotifications.length === 0 && (
        <Box sx={{ p: 3, textAlign: 'center' }}>
          <Typography variant="body2" color="text.secondary">
            No notifications
          </Typography>
        </Box>
      )}

      {!loading && !error && recentNotifications.length > 0 && (
        <>
          <List sx={{ maxHeight: 350, overflow: 'auto', p: 0 }}>
            {recentNotifications.map((notification: Notification) => (
              <ListItem
                key={notification.id}
                sx={{
                  bgcolor: notification.readAt ? 'transparent' : 'action.hover',
                  borderBottom: '1px solid',
                  borderColor: 'divider',
                  cursor: 'pointer',
                  '&:hover': {
                    bgcolor: 'action.selected',
                  },
                }}
                secondaryAction={
                  !notification.readAt && (
                    <IconButton
                      edge="end"
                      size="small"
                      onClick={(e) => handleMarkAsRead(notification.id, e)}
                      title="Mark as read"
                    >
                      <CheckCircle fontSize="small" />
                    </IconButton>
                  )
                }
              >
                <Box sx={{ display: 'flex', gap: 1, width: '100%', pr: 4 }}>
                  <Box sx={{ mt: 0.5 }}>{getSeverityIcon(notification.severity)}</Box>
                  <Box sx={{ flex: 1, minWidth: 0 }}>
                    <ListItemText
                      primary={
                        <Typography
                          variant="body2"
                          fontWeight={notification.readAt ? 'normal' : 'bold'}
                          noWrap
                        >
                          {notification.title}
                        </Typography>
                      }
                      secondary={
                        <>
                          <Typography
                            variant="body2"
                            color="text.secondary"
                            sx={{
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              display: '-webkit-box',
                              WebkitLineClamp: 2,
                              WebkitBoxOrient: 'vertical',
                            }}
                          >
                            {notification.message}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {formatDistanceToNow(new Date(notification.createdAt), { addSuffix: true })}
                          </Typography>
                        </>
                      }
                    />
                  </Box>
                </Box>
              </ListItem>
            ))}
          </List>
          <Divider />
          <Box sx={{ p: 1, textAlign: 'center' }}>
            <Button fullWidth onClick={handleViewAll}>
              View All Notifications
            </Button>
          </Box>
        </>
      )}
    </Box>
  );
}
