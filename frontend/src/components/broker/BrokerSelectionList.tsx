import { useState, useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  CardActions,
  Typography,
  Button,
  Grid,
  CircularProgress,
  Alert,
  Chip,
} from '@mui/material';
import { Link as LinkIcon } from '@mui/icons-material';
import type { BrokerInfo } from '../../types';
import { apiClient } from '../../services/api';

interface BrokerSelectionListProps {
  onSelectBroker: (broker: BrokerInfo) => void;
}

export default function BrokerSelectionList({ onSelectBroker }: BrokerSelectionListProps) {
  const [brokers, setBrokers] = useState<BrokerInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadBrokers();
  }, []);

  const loadBrokers = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.listBrokers();
      setBrokers(data.brokers || []);
    } catch (err: any) {
      setError(err.response?.data?.message || 'Failed to load available brokers');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
      </Alert>
    );
  }

  if (brokers.length === 0) {
    return (
      <Alert severity="info">
        No broker connectors are currently available. Please contact support.
      </Alert>
    );
  }

  return (
    <Grid container spacing={3}>
      {brokers.map((broker) => (
        <Grid key={broker.name} size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                {broker.name}
              </Typography>
              <Typography variant="body2" color="text.secondary" paragraph>
                {broker.description}
              </Typography>
              <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
                Version: {broker.version}
              </Typography>
              
              <Box sx={{ mt: 2 }}>
                <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
                  Supported Exchanges:
                </Typography>
                <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                  {broker.supportedExchanges.map((exchange) => (
                    <Chip key={exchange} label={exchange} size="small" />
                  ))}
                </Box>
              </Box>

              <Box sx={{ mt: 2 }}>
                <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
                  Supported Order Types:
                </Typography>
                <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
                  {broker.supportedOrderTypes.map((orderType) => (
                    <Chip key={orderType} label={orderType} size="small" variant="outlined" />
                  ))}
                </Box>
              </Box>
            </CardContent>
            <CardActions>
              <Button
                size="small"
                variant="contained"
                startIcon={<LinkIcon />}
                onClick={() => onSelectBroker(broker)}
              >
                Connect
              </Button>
            </CardActions>
          </Card>
        </Grid>
      ))}
    </Grid>
  );
}
