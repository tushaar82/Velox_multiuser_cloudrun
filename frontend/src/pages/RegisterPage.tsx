import { useState, useEffect } from 'react';
import { useNavigate, Link as RouterLink } from 'react-router-dom';
import {
  Box,
  TextField,
  Button,
  Typography,
  Alert,
  Link,
  InputAdornment,
  IconButton,
  CircularProgress,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  FormHelperText,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import { Visibility, VisibilityOff, CheckCircle, Cancel } from '@mui/icons-material';
import { useAppDispatch, useAppSelector } from '../store/hooks';
import { register, clearError } from '../store/slices/authSlice';
import { UserRole } from '../types';

interface PasswordRequirement {
  label: string;
  test: (password: string) => boolean;
}

const passwordRequirements: PasswordRequirement[] = [
  { label: 'At least 8 characters', test: (pwd) => pwd.length >= 8 },
  { label: 'At least one uppercase letter', test: (pwd) => /[A-Z]/.test(pwd) },
  { label: 'At least one number', test: (pwd) => /\d/.test(pwd) },
  { label: 'At least one special character', test: (pwd) => /[!@#$%^&*(),.?":{}|<>]/.test(pwd) },
];

export default function RegisterPage() {
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const { loading, error, isAuthenticated } = useAppSelector((state) => state.auth);

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [role, setRole] = useState<UserRole>(UserRole.TRADER);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const [validationErrors, setValidationErrors] = useState<{
    email?: string;
    password?: string;
    confirmPassword?: string;
    role?: string;
  }>({});
  const [registrationSuccess, setRegistrationSuccess] = useState(false);

  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, navigate]);

  useEffect(() => {
    return () => {
      dispatch(clearError());
    };
  }, [dispatch]);

  const validateForm = () => {
    const errors: {
      email?: string;
      password?: string;
      confirmPassword?: string;
      role?: string;
    } = {};

    // Email validation
    if (!email) {
      errors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      errors.email = 'Invalid email format';
    }

    // Password validation
    if (!password) {
      errors.password = 'Password is required';
    } else {
      const failedRequirements = passwordRequirements.filter((req) => !req.test(password));
      if (failedRequirements.length > 0) {
        errors.password = 'Password does not meet all requirements';
      }
    }

    // Confirm password validation
    if (!confirmPassword) {
      errors.confirmPassword = 'Please confirm your password';
    } else if (password !== confirmPassword) {
      errors.confirmPassword = 'Passwords do not match';
    }

    // Role validation
    if (!role) {
      errors.role = 'Please select a role';
    }

    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    try {
      await dispatch(register({ email, password, role })).unwrap();
      setRegistrationSuccess(true);
      // Redirect to login after 2 seconds
      setTimeout(() => {
        navigate('/login');
      }, 2000);
    } catch (err) {
      // Error is handled by Redux state
    }
  };

  const handleTogglePasswordVisibility = () => {
    setShowPassword(!showPassword);
  };

  const handleToggleConfirmPasswordVisibility = () => {
    setShowConfirmPassword(!showConfirmPassword);
  };

  const getPasswordRequirementStatus = (requirement: PasswordRequirement) => {
    if (!password) return null;
    return requirement.test(password);
  };

  return (
    <Box component="form" onSubmit={handleSubmit} noValidate>
      {registrationSuccess && (
        <Alert severity="success" sx={{ mb: 2 }}>
          Registration successful! Redirecting to login...
        </Alert>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <TextField
        fullWidth
        label="Email"
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        error={!!validationErrors.email}
        helperText={validationErrors.email}
        margin="normal"
        autoComplete="email"
        disabled={loading || registrationSuccess}
      />

      <TextField
        fullWidth
        label="Password"
        type={showPassword ? 'text' : 'password'}
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        error={!!validationErrors.password}
        helperText={validationErrors.password}
        margin="normal"
        autoComplete="new-password"
        disabled={loading || registrationSuccess}
        slotProps={{
          input: {
            endAdornment: (
              <InputAdornment position="end">
                <IconButton
                  aria-label="toggle password visibility"
                  onClick={handleTogglePasswordVisibility}
                  edge="end"
                  disabled={loading || registrationSuccess}
                >
                  {showPassword ? <VisibilityOff /> : <Visibility />}
                </IconButton>
              </InputAdornment>
            ),
          },
        }}
      />

      {password && (
        <Box sx={{ mt: 1, mb: 1 }}>
          <Typography variant="caption" color="text.secondary" sx={{ mb: 0.5, display: 'block' }}>
            Password Requirements:
          </Typography>
          <List dense disablePadding>
            {passwordRequirements.map((requirement, index) => {
              const status = getPasswordRequirementStatus(requirement);
              return (
                <ListItem key={index} disablePadding sx={{ py: 0 }}>
                  <ListItemIcon sx={{ minWidth: 32 }}>
                    {status === true ? (
                      <CheckCircle color="success" fontSize="small" />
                    ) : status === false ? (
                      <Cancel color="error" fontSize="small" />
                    ) : (
                      <Cancel color="disabled" fontSize="small" />
                    )}
                  </ListItemIcon>
                  <ListItemText
                    primary={requirement.label}
                    primaryTypographyProps={{
                      variant: 'caption',
                      color: status === true ? 'success.main' : status === false ? 'error.main' : 'text.secondary',
                    }}
                  />
                </ListItem>
              );
            })}
          </List>
        </Box>
      )}

      <TextField
        fullWidth
        label="Confirm Password"
        type={showConfirmPassword ? 'text' : 'password'}
        value={confirmPassword}
        onChange={(e) => setConfirmPassword(e.target.value)}
        error={!!validationErrors.confirmPassword}
        helperText={validationErrors.confirmPassword}
        margin="normal"
        autoComplete="new-password"
        disabled={loading || registrationSuccess}
        slotProps={{
          input: {
            endAdornment: (
              <InputAdornment position="end">
                <IconButton
                  aria-label="toggle confirm password visibility"
                  onClick={handleToggleConfirmPasswordVisibility}
                  edge="end"
                  disabled={loading || registrationSuccess}
                >
                  {showConfirmPassword ? <VisibilityOff /> : <Visibility />}
                </IconButton>
              </InputAdornment>
            ),
          },
        }}
      />

      <FormControl fullWidth margin="normal" error={!!validationErrors.role}>
        <InputLabel id="role-select-label">Role</InputLabel>
        <Select
          labelId="role-select-label"
          id="role-select"
          value={role}
          label="Role"
          onChange={(e) => setRole(e.target.value as UserRole)}
          disabled={loading || registrationSuccess}
        >
          <MenuItem value={UserRole.TRADER}>
            <Box>
              <Typography variant="body2">Trader</Typography>
              <Typography variant="caption" color="text.secondary">
                Create and execute trading strategies
              </Typography>
            </Box>
          </MenuItem>
          <MenuItem value={UserRole.INVESTOR}>
            <Box>
              <Typography variant="body2">Investor</Typography>
              <Typography variant="caption" color="text.secondary">
                View trading activity (read-only access)
              </Typography>
            </Box>
          </MenuItem>
          <MenuItem value={UserRole.ADMIN}>
            <Box>
              <Typography variant="body2">Admin</Typography>
              <Typography variant="caption" color="text.secondary">
                Manage platform and monitor all users
              </Typography>
            </Box>
          </MenuItem>
        </Select>
        {validationErrors.role && <FormHelperText>{validationErrors.role}</FormHelperText>}
      </FormControl>

      <Button
        type="submit"
        fullWidth
        variant="contained"
        size="large"
        disabled={loading || registrationSuccess}
        sx={{ mt: 3, mb: 2 }}
      >
        {loading ? <CircularProgress size={24} /> : 'Register'}
      </Button>

      <Box sx={{ textAlign: 'center' }}>
        <Typography variant="body2">
          Already have an account?{' '}
          <Link component={RouterLink} to="/login" underline="hover">
            Login here
          </Link>
        </Typography>
      </Box>
    </Box>
  );
}
