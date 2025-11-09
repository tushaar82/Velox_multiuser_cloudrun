import { useEffect, useState } from 'react';
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
  CircularProgress,
  Alert,
  TextField,
  Button,
  Grid,
  Chip,
  TablePagination,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
} from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { Search as SearchIcon, Refresh as RefreshIcon } from '@mui/icons-material';
import { apiClient } from '../../services/api';

interface AuditLog {
  id: string;
  timestamp: string;
  user_id: string;
  user_email: string;
  action: string;
  resource: string;
  resource_id: string;
  ip_address: string;
  result: 'success' | 'failure';
  details: any;
}

const ACTION_TYPES = [
  'login',
  'logout',
  'register',
  'order_submit',
  'order_cancel',
  'strategy_activate',
  'strategy_pause',
  'strategy_stop',
  'broker_connect',
  'broker_disconnect',
  'user_disable',
  'user_enable',
];

export function AuditLogViewer() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  
  // Filters
  const [startDate, setStartDate] = useState<Date | null>(null);
  const [endDate, setEndDate] = useState<Date | null>(null);
  const [userIdFilter, setUserIdFilter] = useState('');
  const [actionTypeFilter, setActionTypeFilter] = useState('');

  const fetchAuditLogs = async () => {
    try {
      setError(null);
      setLoading(true);
      
      const filters: any = {
        limit: 1000, // Fetch more for client-side pagination
      };
      
      if (startDate) {
        filters.start_date = startDate.toISOString().split('T')[0];
      }
      if (endDate) {
        filters.end_date = endDate.toISOString().split('T')[0];
      }
      if (userIdFilter) {
        filters.user_id = userIdFilter;
      }
      if (actionTypeFilter) {
        filters.action_type = actionTypeFilter;
      }

      const response = await apiClient.getAuditLogs(filters);
      setLogs(response.logs);
      setPage(0); // Reset to first page when filters change
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to fetch audit logs');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditLogs();
  }, []);

  const handleSearch = () => {
    fetchAuditLogs();
  };

  const handleReset = () => {
    setStartDate(null);
    setEndDate(null);
    setUserIdFilter('');
    setActionTypeFilter('');
  };

  const handleChangePage = (_: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const getActionColor = (action: string) => {
    if (action.includes('login') || action.includes('register')) return 'info';
    if (action.includes('activate') || action.includes('connect')) return 'success';
    if (action.includes('disable') || action.includes('cancel') || action.includes('stop')) return 'error';
    if (action.includes('pause') || action.includes('disconnect')) return 'warning';
    return 'default';
  };

  const getResultColor = (result: string) => {
    return result === 'success' ? 'success' : 'error';
  };

  const paginatedLogs = logs.slice(page * rowsPerPage, page * rowsPerPage + rowsPerPage);

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <Box>
        <Typography variant="h6" gutterBottom>
          Audit Log Viewer
        </Typography>

        {/* Filters */}
        <Paper sx={{ p: 2, mb: 3 }}>
          <Grid container spacing={2} alignItems="center">
            <Grid item xs={12} sm={6} md={3}>
              <DatePicker
                label="Start Date"
                value={startDate}
                onChange={(newValue) => setStartDate(newValue)}
                slotProps={{ textField: { fullWidth: true, size: 'small' } }}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <DatePicker
                label="End Date"
                value={endDate}
                onChange={(newValue) => setEndDate(newValue)}
                slotProps={{ textField: { fullWidth: true, size: 'small' } }}
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <TextField
                fullWidth
                size="small"
                label="User ID"
                value={userIdFilter}
                onChange={(e) => setUserIdFilter(e.target.value)}
                placeholder="Filter by user ID"
              />
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <FormControl fullWidth size="small">
                <InputLabel>Action Type</InputLabel>
                <Select
                  value={actionTypeFilter}
                  label="Action Type"
                  onChange={(e) => setActionTypeFilter(e.target.value)}
                >
                  <MenuItem value="">All Actions</MenuItem>
                  {ACTION_TYPES.map((action) => (
                    <MenuItem key={action} value={action}>
                      {action.replace(/_/g, ' ').toUpperCase()}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Button
                fullWidth
                variant="contained"
                startIcon={<SearchIcon />}
                onClick={handleSearch}
              >
                Search
              </Button>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Button fullWidth variant="outlined" onClick={handleReset}>
                Reset Filters
              </Button>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <Button
                fullWidth
                variant="outlined"
                startIcon={<RefreshIcon />}
                onClick={fetchAuditLogs}
              >
                Refresh
              </Button>
            </Grid>
          </Grid>
        </Paper>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {loading ? (
          <Box display="flex" justifyContent="center" alignItems="center" minHeight={400}>
            <CircularProgress />
          </Box>
        ) : (
          <>
            <TableContainer component={Paper}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Timestamp</TableCell>
                    <TableCell>User</TableCell>
                    <TableCell>Action</TableCell>
                    <TableCell>Resource</TableCell>
                    <TableCell>IP Address</TableCell>
                    <TableCell align="center">Result</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {paginatedLogs.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6} align="center">
                        <Typography variant="body2" color="text.secondary" py={4}>
                          No audit logs found
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ) : (
                    paginatedLogs.map((log) => (
                      <TableRow key={log.id} hover>
                        <TableCell>
                          <Typography variant="body2">
                            {new Date(log.timestamp).toLocaleString()}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" fontWeight="medium">
                            {log.user_email}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {log.user_id}
                          </Typography>
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={log.action.replace(/_/g, ' ').toUpperCase()}
                            size="small"
                            color={getActionColor(log.action)}
                          />
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2">{log.resource}</Typography>
                          {log.resource_id && (
                            <Typography variant="caption" color="text.secondary">
                              {log.resource_id}
                            </Typography>
                          )}
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2" fontFamily="monospace">
                            {log.ip_address}
                          </Typography>
                        </TableCell>
                        <TableCell align="center">
                          <Chip
                            label={log.result.toUpperCase()}
                            size="small"
                            color={getResultColor(log.result)}
                          />
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
            </TableContainer>
            <TablePagination
              rowsPerPageOptions={[10, 25, 50, 100]}
              component="div"
              count={logs.length}
              rowsPerPage={rowsPerPage}
              page={page}
              onPageChange={handleChangePage}
              onRowsPerPageChange={handleChangeRowsPerPage}
            />
          </>
        )}
      </Box>
    </LocalizationProvider>
  );
}
