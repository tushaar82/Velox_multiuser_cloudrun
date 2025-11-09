import { Alert, Box, Chip, Tooltip } from '@mui/material';
import { Lock as LockIcon, Visibility as ViewIcon } from '@mui/icons-material';

interface ReadOnlyIndicatorProps {
  variant?: 'banner' | 'chip' | 'icon';
  message?: string;
}

export default function ReadOnlyIndicator({ 
  variant = 'banner',
  message = 'You have read-only access to this account. You cannot modify strategies or execute trades.'
}: ReadOnlyIndicatorProps) {
  
  if (variant === 'chip') {
    return (
      <Tooltip title={message}>
        <Chip
          icon={<ViewIcon />}
          label="Read-Only"
          color="info"
          size="small"
          sx={{ fontWeight: 500 }}
        />
      </Tooltip>
    );
  }

  if (variant === 'icon') {
    return (
      <Tooltip title={message}>
        <Box
          sx={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: 0.5,
            color: 'info.main',
            cursor: 'help',
          }}
        >
          <LockIcon fontSize="small" />
        </Box>
      </Tooltip>
    );
  }

  // Default banner variant
  return (
    <Alert severity="info" icon={<ViewIcon />} sx={{ mb: 2 }}>
      {message}
    </Alert>
  );
}
