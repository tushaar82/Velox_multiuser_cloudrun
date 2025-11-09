import { useEffect, useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  LinearProgress,
} from '@mui/material';
import { useAppDispatch, useAppSelector } from '../../store/hooks';
import { refreshSession, setSessionTimeoutWarning, logout } from '../../store/slices/authSlice';

const WARNING_TIME = 5 * 60 * 1000; // 5 minutes before timeout
const SESSION_TIMEOUT = 30 * 60 * 1000; // 30 minutes total
const COUNTDOWN_DURATION = 60; // 60 seconds countdown

export default function SessionTimeoutWarning() {
  const dispatch = useAppDispatch();
  const { sessionTimeoutWarning, isAuthenticated } = useAppSelector((state) => state.auth);
  const [countdown, setCountdown] = useState(COUNTDOWN_DURATION);
  const [lastActivity, setLastActivity] = useState(Date.now());

  useEffect(() => {
    if (!isAuthenticated) return;

    // Track user activity
    const activityEvents = ['mousedown', 'keydown', 'scroll', 'touchstart'];
    
    const handleActivity = () => {
      setLastActivity(Date.now());
      if (sessionTimeoutWarning) {
        dispatch(setSessionTimeoutWarning(false));
        setCountdown(COUNTDOWN_DURATION);
      }
    };

    activityEvents.forEach((event) => {
      window.addEventListener(event, handleActivity);
    });

    // Check for inactivity
    const inactivityInterval = setInterval(() => {
      const timeSinceLastActivity = Date.now() - lastActivity;
      
      if (timeSinceLastActivity >= SESSION_TIMEOUT) {
        // Session timeout - logout user
        dispatch(logout());
      } else if (timeSinceLastActivity >= SESSION_TIMEOUT - WARNING_TIME && !sessionTimeoutWarning) {
        // Show warning
        dispatch(setSessionTimeoutWarning(true));
        setCountdown(COUNTDOWN_DURATION);
      }
    }, 1000);

    return () => {
      activityEvents.forEach((event) => {
        window.removeEventListener(event, handleActivity);
      });
      clearInterval(inactivityInterval);
    };
  }, [isAuthenticated, lastActivity, sessionTimeoutWarning, dispatch]);

  useEffect(() => {
    if (!sessionTimeoutWarning) return;

    // Countdown timer
    const countdownInterval = setInterval(() => {
      setCountdown((prev) => {
        if (prev <= 1) {
          // Time's up - logout
          dispatch(logout());
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(countdownInterval);
  }, [sessionTimeoutWarning, dispatch]);

  const handleStayLoggedIn = async () => {
    try {
      await dispatch(refreshSession()).unwrap();
      dispatch(setSessionTimeoutWarning(false));
      setLastActivity(Date.now());
      setCountdown(COUNTDOWN_DURATION);
    } catch (error) {
      // If refresh fails, logout
      dispatch(logout());
    }
  };

  const handleLogout = () => {
    dispatch(logout());
  };

  const progress = (countdown / COUNTDOWN_DURATION) * 100;

  return (
    <Dialog
      open={sessionTimeoutWarning}
      onClose={() => {}} // Prevent closing by clicking outside
      maxWidth="sm"
      fullWidth
    >
      <DialogTitle>Session Timeout Warning</DialogTitle>
      <DialogContent>
        <Typography variant="body1" gutterBottom>
          Your session is about to expire due to inactivity.
        </Typography>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          You will be automatically logged out in {countdown} seconds.
        </Typography>
        <LinearProgress
          variant="determinate"
          value={progress}
          color={countdown <= 10 ? 'error' : 'primary'}
          sx={{ mt: 2 }}
        />
      </DialogContent>
      <DialogActions>
        <Button onClick={handleLogout} color="inherit">
          Logout Now
        </Button>
        <Button onClick={handleStayLoggedIn} variant="contained" autoFocus>
          Stay Logged In
        </Button>
      </DialogActions>
    </Dialog>
  );
}
