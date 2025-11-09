import { useState } from 'react';
import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  Chip,
  IconButton,
  Tooltip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
} from '@mui/material';
import { Close, Edit } from '@mui/icons-material';
import type { Position } from '../../types';
import { useAppDispatch } from '../../store/hooks';
import { closePosition, updateTrailingStopLoss } from '../../store/slices/positionSlice';

interface ActivePositionsTableProps {
  positions: Position[];
  loading: boolean;
}

export default function ActivePositionsTable({ positions, loading }: ActivePositionsTableProps) {
  const dispatch = useAppDispatch();
  const [trailingStopDialog, setTrailingStopDialog] = useState(false);
  const [selectedPosition, setSelectedPosition] = useState<Position | null>(null);
  const [trailingStopPercentage, setTrailingStopPercentage] = useState('');

  const openPositions = positions.filter((p) => !p.closedAt);

  const handleClosePosition = (positionId: string) => {
    if (window.confirm('Are you sure you want to close this position?')) {
      dispatch(closePosition(positionId));
    }
  };

  const handleOpenTrailingStopDialog = (position: Position) => {
    setSelectedPosition(position);
    setTrailingStopPercentage(
      position.trailingStopLoss?.percentage?.toString() || ''
    );
    setTrailingStopDialog(true);
  };

  const handleCloseTrailingStopDialog = () => {
    setTrailingStopDialog(false);
    setSelectedPosition(null);
    setTrailingStopPercentage('');
  };

  const handleUpdateTrailingStop = () => {
    if (selectedPosition && trailingStopPercentage) {
      const percentage = parseFloat(trailingStopPercentage);
      if (percentage >= 0.1 && percentage <= 10) {
        dispatch(
          updateTrailingStopLoss({
            positionId: selectedPosition.id,
            config: {
              enabled: true,
              percentage,
            },
          })
        );
        handleCloseTrailingStopDialog();
      }
    }
  };

  if (loading) {
    return (
      <Box sx={{ mb: 3 }}>
        <Typography variant="body2" color="text.secondary">
          Loading positions...
        </Typography>
      </Box>
    );
  }

  return (
    <>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>
          Active Positions ({openPositions.length})
        </Typography>
        {openPositions.length === 0 ? (
          <Paper sx={{ p: 3, textAlign: 'center' }}>
            <Typography color="text.secondary">No active positions</Typography>
          </Paper>
        ) : (
          <TableContainer component={Paper}>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Symbol</TableCell>
                  <TableCell>Side</TableCell>
                  <TableCell align="right">Quantity</TableCell>
                  <TableCell align="right">Entry Price</TableCell>
                  <TableCell align="right">Current Price</TableCell>
                  <TableCell align="right">Unrealized P&L</TableCell>
                  <TableCell align="right">P&L %</TableCell>
                  <TableCell>Trailing Stop</TableCell>
                  <TableCell align="center">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {openPositions.map((position) => {
                  const pnlPercent =
                    ((position.currentPrice - position.entryPrice) / position.entryPrice) *
                    100 *
                    (position.side === 'long' ? 1 : -1);
                  const isProfitable = position.unrealizedPnl >= 0;

                  return (
                    <TableRow key={position.id} hover>
                      <TableCell>
                        <Typography variant="body2" fontWeight="medium">
                          {position.symbol}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={position.side.toUpperCase()}
                          color={position.side === 'long' ? 'success' : 'error'}
                          size="small"
                        />
                      </TableCell>
                      <TableCell align="right">{position.quantity}</TableCell>
                      <TableCell align="right">
                        ₹{position.entryPrice.toFixed(2)}
                      </TableCell>
                      <TableCell align="right">
                        ₹{position.currentPrice.toFixed(2)}
                      </TableCell>
                      <TableCell
                        align="right"
                        sx={{ color: isProfitable ? 'success.main' : 'error.main' }}
                      >
                        ₹{position.unrealizedPnl.toFixed(2)}
                      </TableCell>
                      <TableCell
                        align="right"
                        sx={{ color: isProfitable ? 'success.main' : 'error.main' }}
                      >
                        {pnlPercent.toFixed(2)}%
                      </TableCell>
                      <TableCell>
                        {position.trailingStopLoss?.enabled ? (
                          <Chip
                            label={`${position.trailingStopLoss.percentage}%`}
                            size="small"
                            color="primary"
                            variant="outlined"
                          />
                        ) : (
                          <Typography variant="body2" color="text.secondary">
                            None
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell align="center">
                        <Tooltip title="Edit Trailing Stop">
                          <IconButton
                            size="small"
                            onClick={() => handleOpenTrailingStopDialog(position)}
                          >
                            <Edit fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Close Position">
                          <IconButton
                            size="small"
                            color="error"
                            onClick={() => handleClosePosition(position.id)}
                          >
                            <Close fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </Box>

      {/* Trailing Stop Loss Dialog */}
      <Dialog open={trailingStopDialog} onClose={handleCloseTrailingStopDialog}>
        <DialogTitle>Configure Trailing Stop Loss</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Set trailing stop loss percentage (0.1% - 10%)
          </Typography>
          <TextField
            autoFocus
            margin="dense"
            label="Percentage"
            type="number"
            fullWidth
            value={trailingStopPercentage}
            onChange={(e) => setTrailingStopPercentage(e.target.value)}
            inputProps={{ min: 0.1, max: 10, step: 0.1 }}
            helperText="Enter a value between 0.1 and 10"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseTrailingStopDialog}>Cancel</Button>
          <Button onClick={handleUpdateTrailingStop} variant="contained">
            Update
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
