import { useEffect, useState } from 'react';
import {
  Snackbar,
  Alert,
  AlertTitle,
  Typography,
  LinearProgress,
  Box,
} from '@mui/material';

interface AccountLockedNotificationProps {
  open: boolean;
  onClose: () => void;
  lockDuration?: number; // in milliseconds, default 15 minutes
}

const DEFAULT_LOCK_DURATION = 15 * 60 * 1000; // 15 minutes

export default function AccountLockedNotification({
  open,
  onClose,
  lockDuration = DEFAULT_LOCK_DURATION,
}: AccountLockedNotificationProps) {
  const [remainingTime, setRemainingTime] = useState(lockDuration);
  const [lockStartTime] = useState(Date.now());

  useEffect(() => {
    if (!open) return;

    const interval = setInterval(() => {
      const elapsed = Date.now() - lockStartTime;
      const remaining = Math.max(0, lockDuration - elapsed);
      
      setRemainingTime(remaining);

      if (remaining === 0) {
        onClose();
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [open, lockStartTime, lockDuration, onClose]);

  const formatTime = (ms: number) => {
    const totalSeconds = Math.floor(ms / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const progress = ((lockDuration - remainingTime) / lockDuration) * 100;

  return (
    <Snackbar
      open={open}
      anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
      onClose={onClose}
    >
      <Alert severity="error" onClose={onClose} sx={{ width: '100%', minWidth: 400 }}>
        <AlertTitle>Account Locked</AlertTitle>
        <Typography variant="body2" gutterBottom>
          Your account has been locked due to multiple failed login attempts.
        </Typography>
        <Typography variant="body2" gutterBottom>
          It will be automatically unlocked in: <strong>{formatTime(remainingTime)}</strong>
        </Typography>
        <Box sx={{ mt: 1 }}>
          <LinearProgress variant="determinate" value={progress} color="inherit" />
        </Box>
      </Alert>
    </Snackbar>
  );
}
