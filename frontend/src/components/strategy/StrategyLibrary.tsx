import { useEffect } from 'react';
import {
  Box,
  Card,
  CardContent,
  CardActions,
  Typography,
  Button,
  Grid,
  Chip,
  CircularProgress,
  Alert,
} from '@mui/material';
import type { Strategy } from '../../types';
import { useAppDispatch, useAppSelector } from '../../store/hooks';
import { fetchStrategies, setSelectedStrategy } from '../../store/slices/strategySlice';
import { useReadOnlyAccess } from '../../hooks/useReadOnlyAccess';

interface StrategyLibraryProps {
  onSelectStrategy: (strategy: Strategy) => void;
}

export default function StrategyLibrary({ onSelectStrategy }: StrategyLibraryProps) {
  const dispatch = useAppDispatch();
  const { strategies, loading, error } = useAppSelector((state) => state.strategy);
  const isReadOnly = useReadOnlyAccess();

  useEffect(() => {
    dispatch(fetchStrategies());
  }, [dispatch]);

  const handleSelectStrategy = (strategy: Strategy) => {
    dispatch(setSelectedStrategy(strategy));
    onSelectStrategy(strategy);
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="300px">
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

  return (
    <Box>
      <Typography variant="h5" gutterBottom>
        Strategy Library
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Select a pre-built strategy to configure and activate
      </Typography>

      <Grid container spacing={3}>
        {strategies.map((strategy) => (
          <Grid size={{ xs: 12, md: 6, lg: 4 }} key={strategy.id}>
            <Card
              sx={{
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                '&:hover': {
                  boxShadow: 6,
                },
              }}
            >
              <CardContent sx={{ flexGrow: 1 }}>
                <Typography variant="h6" gutterBottom>
                  {strategy.name}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  {strategy.description}
                </Typography>

                <Box sx={{ mb: 1 }}>
                  <Typography variant="caption" color="text.secondary">
                    Timeframes:
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 0.5 }}>
                    {strategy.config.timeframes.map((tf) => (
                      <Chip key={tf} label={tf} size="small" />
                    ))}
                  </Box>
                </Box>

                <Box>
                  <Typography variant="caption" color="text.secondary">
                    Symbols:
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap', mt: 0.5 }}>
                    {strategy.config.symbols.slice(0, 3).map((symbol) => (
                      <Chip key={symbol} label={symbol} size="small" variant="outlined" />
                    ))}
                    {strategy.config.symbols.length > 3 && (
                      <Chip
                        label={`+${strategy.config.symbols.length - 3} more`}
                        size="small"
                        variant="outlined"
                      />
                    )}
                  </Box>
                </Box>
              </CardContent>

              <CardActions>
                <Button
                  size="small"
                  variant="contained"
                  fullWidth
                  onClick={() => handleSelectStrategy(strategy)}
                  disabled={isReadOnly}
                >
                  {isReadOnly ? 'View Only' : 'Configure & Activate'}
                </Button>
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>

      {strategies.length === 0 && !loading && (
        <Alert severity="info">
          No strategies available. Please contact your administrator.
        </Alert>
      )}
    </Box>
  );
}
