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
} from '@mui/material';
import { Cancel } from '@mui/icons-material';
import type { Order } from '../../types';
import { useAppDispatch } from '../../store/hooks';
import { cancelOrder } from '../../store/slices/orderSlice';

interface ActiveOrdersTableProps {
  orders: Order[];
  loading: boolean;
}

export default function ActiveOrdersTable({ orders, loading }: ActiveOrdersTableProps) {
  const dispatch = useAppDispatch();

  const activeOrders = orders.filter(
    (o) => o.status === 'pending' || o.status === 'submitted' || o.status === 'partial'
  );

  const handleCancelOrder = (orderId: string) => {
    if (window.confirm('Are you sure you want to cancel this order?')) {
      dispatch(cancelOrder(orderId));
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'pending':
        return 'warning';
      case 'submitted':
        return 'info';
      case 'partial':
        return 'primary';
      case 'filled':
        return 'success';
      case 'cancelled':
        return 'default';
      case 'rejected':
        return 'error';
      default:
        return 'default';
    }
  };

  if (loading) {
    return (
      <Box sx={{ mb: 3 }}>
        <Typography variant="body2" color="text.secondary">
          Loading orders...
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ mb: 3 }}>
      <Typography variant="h6" sx={{ mb: 2 }}>
        Active Orders ({activeOrders.length})
      </Typography>
      {activeOrders.length === 0 ? (
        <Paper sx={{ p: 3, textAlign: 'center' }}>
          <Typography color="text.secondary">No active orders</Typography>
        </Paper>
      ) : (
        <TableContainer component={Paper}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Symbol</TableCell>
                <TableCell>Side</TableCell>
                <TableCell>Type</TableCell>
                <TableCell align="right">Quantity</TableCell>
                <TableCell align="right">Price</TableCell>
                <TableCell align="right">Filled</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Time</TableCell>
                <TableCell align="center">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {activeOrders.map((order) => (
                <TableRow key={order.id} hover>
                  <TableCell>
                    <Typography variant="body2" fontWeight="medium">
                      {order.symbol}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={order.side.toUpperCase()}
                      color={order.side === 'buy' ? 'success' : 'error'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ textTransform: 'capitalize' }}>
                      {order.orderType.replace('_', ' ')}
                    </Typography>
                  </TableCell>
                  <TableCell align="right">{order.quantity}</TableCell>
                  <TableCell align="right">
                    {order.price ? `₹${order.price.toFixed(2)}` : 'Market'}
                  </TableCell>
                  <TableCell align="right">
                    {order.filledQuantity} / {order.quantity}
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={order.status.toUpperCase()}
                      color={getStatusColor(order.status) as any}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" color="text.secondary">
                      {new Date(order.createdAt).toLocaleTimeString()}
                    </Typography>
                  </TableCell>
                  <TableCell align="center">
                    {(order.status === 'pending' || order.status === 'submitted') && (
                      <Tooltip title="Cancel Order">
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => handleCancelOrder(order.id)}
                        >
                          <Cancel fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );
}
