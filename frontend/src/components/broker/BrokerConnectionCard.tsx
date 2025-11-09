import { useState } from 'react';
import {
  Card,
  CardContent,
  CardActions,
  Typography,
  Button,
  Chip,
  Box,
  CircularProgress,
} from '@mui/material';
import {
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  LinkOff as LinkOffIcon,
} from '@mui/icons-material';
import type { BrokerConnection } from '../../types';

interface BrokerConnectionCardProps {
  connection: BrokerConnection;
  onDisconnect: (connectionId: string) => void;
  loading?: boolean;
}

export default function BrokerConnectionCard({
  connection,
  onDisconnect,
  loading = false,
}: BrokerConnectionCardProps) {
  const [disconnecting, setDisconnecting] = useState(false);

  const handleDisconnect = async () => {
    setDisconnecting(true);
    try {
      await onDisconnect(connection.id);
    } finally {
      setDisconnecting(false);
    }
  };

  return (
    <Card>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
          <Typography variant="h6" component="div">
            {connection.brokerName}
          </Typography>
          <Chip
            icon={connection.isConnected ? <CheckCircleIcon /> : <ErrorIcon />}
            label={connection.isConnected ? 'Connected' : 'Disconnected'}
            color={connection.isConnected ? 'success' : 'error'}
            size="small"
          />
        </Box>

        <Typography variant="body2" color="text.secondary" gutterBottom>
          Connection ID: {connection.id}
        </Typography>

        {connection.lastConnectedAt && (
          <Typography variant="body2" color="text.secondary">
            Last connected: {new Date(connection.lastConnectedAt).toLocaleString()}
          </Typography>
        )}

        <Typography variant="body2" color="text.secondary">
          Created: {new Date(connection.createdAt).toLocaleString()}
        </Typography>
      </CardContent>

      <CardActions>
        <Button
          size="small"
          color="error"
          startIcon={disconnecting ? <CircularProgress size={16} /> : <LinkOffIcon />}
          onClick={handleDisconnect}
          disabled={disconnecting || loading}
        >
          Disconnect
        </Button>
      </CardActions>
    </Card>
  );
}
