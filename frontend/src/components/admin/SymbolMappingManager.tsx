import { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Button,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  CircularProgress,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TablePagination,
  Chip,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Snackbar,
} from '@mui/material';
import { Upload, Refresh, Search, CheckCircle, Error as ErrorIcon } from '@mui/icons-material';
import { apiClient } from '../../services/api';

interface SymbolMapping {
  standard_symbol: string;
  broker_symbol: string;
  broker_token: string;
  exchange: string;
  instrument_type: string;
  lot_size: number;
  tick_size: number;
}

interface UploadResult {
  success: boolean;
  loaded?: number;
  failed?: number;
  errors?: string[];
  error?: string;
}

const BROKERS = ['Angel One', 'Upstox', 'Fyers'];

export function SymbolMappingManager() {
  const [selectedBroker, setSelectedBroker] = useState<string>('Angel One');
  const [mappings, setMappings] = useState<SymbolMapping[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [validateDialogOpen, setValidateDialogOpen] = useState(false);
  const [validateSymbol, setValidateSymbol] = useState('');
  const [validating, setValidating] = useState(false);
  const [validationResult, setValidationResult] = useState<{ valid: boolean; broker_token?: string; error?: string } | null>(null);
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' | 'info' }>({
    open: false,
    message: '',
    severity: 'info',
  });

  useEffect(() => {
    loadMappings();
  }, [selectedBroker]);

  const loadMappings = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await apiClient.getSymbolMappings(selectedBroker);
      setMappings(response.mappings || []);
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to load symbol mappings');
      setMappings([]);
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      if (!file.name.endsWith('.csv')) {
        setError('Please select a CSV file');
        return;
      }
      setSelectedFile(file);
      setUploadResult(null);
      setError(null);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setError('Please select a file first');
      return;
    }

    setUploading(true);
    setUploadResult(null);
    setError(null);

    try {
      const result = await apiClient.uploadSymbolMapping(selectedBroker, selectedFile);
      setUploadResult(result);
      
      if (result.success) {
        // Reload mappings after successful upload
        await loadMappings();
        setSelectedFile(null);
        // Reset file input
        const fileInput = document.getElementById('csv-file-input') as HTMLInputElement;
        if (fileInput) fileInput.value = '';
      }
    } catch (err: any) {
      setError(err.response?.data?.error || 'Failed to upload symbol mappings');
    } finally {
      setUploading(false);
    }
  };

  const handleChangePage = (_event: unknown, newPage: number) => {
    setPage(newPage);
  };

  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  const handleValidateSymbol = async () => {
    if (!validateSymbol.trim()) {
      setSnackbar({ open: true, message: 'Please enter a symbol to validate', severity: 'error' });
      return;
    }

    setValidating(true);
    setValidationResult(null);

    try {
      const result = await apiClient.validateSymbol(selectedBroker, validateSymbol.trim());
      setValidationResult(result);
      setSnackbar({
        open: true,
        message: result.valid ? 'Symbol is valid!' : 'Symbol not found',
        severity: result.valid ? 'success' : 'error',
      });
    } catch (err: any) {
      const errorMsg = err.response?.data?.error || 'Failed to validate symbol';
      setValidationResult({ valid: false, error: errorMsg });
      setSnackbar({ open: true, message: errorMsg, severity: 'error' });
    } finally {
      setValidating(false);
    }
  };

  const handleCloseValidateDialog = () => {
    setValidateDialogOpen(false);
    setValidateSymbol('');
    setValidationResult(null);
  };

  const handleCloseSnackbar = () => {
    setSnackbar({ ...snackbar, open: false });
  };

  const paginatedMappings = mappings.slice(
    page * rowsPerPage,
    page * rowsPerPage + rowsPerPage
  );

  return (
    <Box>
      <Typography variant="h6" gutterBottom>
        Symbol Mapping Management
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Upload and manage symbol mappings for different brokers
      </Typography>

      {/* Broker Selection and Upload */}
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-end', mb: 2 }}>
          <FormControl sx={{ minWidth: 200 }}>
            <InputLabel>Broker</InputLabel>
            <Select
              value={selectedBroker}
              label="Broker"
              onChange={(e) => setSelectedBroker(e.target.value)}
            >
              {BROKERS.map((broker) => (
                <MenuItem key={broker} value={broker}>
                  {broker}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <Button
            variant="outlined"
            startIcon={<Refresh />}
            onClick={loadMappings}
            disabled={loading}
          >
            Refresh
          </Button>

          <Button
            variant="outlined"
            startIcon={<Search />}
            onClick={() => setValidateDialogOpen(true)}
          >
            Validate Symbol
          </Button>
        </Box>

        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <input
            id="csv-file-input"
            type="file"
            accept=".csv"
            onChange={handleFileSelect}
            style={{ display: 'none' }}
          />
          <label htmlFor="csv-file-input">
            <Button variant="outlined" component="span">
              Choose CSV File
            </Button>
          </label>

          {selectedFile && (
            <Typography variant="body2" color="text.secondary">
              {selectedFile.name}
            </Typography>
          )}

          <Button
            variant="contained"
            startIcon={uploading ? <CircularProgress size={20} /> : <Upload />}
            onClick={handleUpload}
            disabled={!selectedFile || uploading}
          >
            Upload
          </Button>
        </Box>

        {/* Upload Result */}
        {uploadResult && (
          <Box sx={{ mt: 2 }}>
            {uploadResult.success ? (
              <Alert severity="success">
                Successfully loaded {uploadResult.loaded} symbol mappings
                {uploadResult.failed && uploadResult.failed > 0 && (
                  <> ({uploadResult.failed} failed)</>
                )}
              </Alert>
            ) : (
              <Alert severity="error">
                Upload failed: {uploadResult.error}
              </Alert>
            )}

            {uploadResult.errors && uploadResult.errors.length > 0 && (
              <Box sx={{ mt: 1 }}>
                <Typography variant="body2" color="error" gutterBottom>
                  Errors:
                </Typography>
                {uploadResult.errors.map((err, idx) => (
                  <Typography key={idx} variant="caption" color="error" display="block">
                    • {err}
                  </Typography>
                ))}
              </Box>
            )}
          </Box>
        )}

        {/* General Error */}
        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}

        {/* CSV Format Help */}
        <Box sx={{ mt: 2, p: 2, bgcolor: 'grey.50', borderRadius: 1 }}>
          <Typography variant="caption" color="text.secondary" display="block" gutterBottom>
            <strong>CSV Format:</strong>
          </Typography>
          <Typography variant="caption" color="text.secondary" display="block" sx={{ fontFamily: 'monospace' }}>
            standard_symbol,broker_symbol,broker_token,exchange,instrument_type,lot_size,tick_size
          </Typography>
          <Typography variant="caption" color="text.secondary" display="block" sx={{ fontFamily: 'monospace' }}>
            RELIANCE,RELIANCE-EQ,2885,NSE,EQ,1,0.05
          </Typography>
        </Box>
      </Paper>

      {/* Mappings Table */}
      <Paper>
        <Box sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
          <Typography variant="h6">
            Symbol Mappings for {selectedBroker}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {mappings.length} mappings loaded
          </Typography>
        </Box>

        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress />
          </Box>
        ) : mappings.length === 0 ? (
          <Box sx={{ p: 4, textAlign: 'center' }}>
            <Typography variant="body1" color="text.secondary">
              No symbol mappings found for {selectedBroker}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
              Upload a CSV file to add mappings
            </Typography>
          </Box>
        ) : (
          <>
            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell>Standard Symbol</TableCell>
                    <TableCell>Broker Symbol</TableCell>
                    <TableCell>Broker Token</TableCell>
                    <TableCell>Exchange</TableCell>
                    <TableCell>Type</TableCell>
                    <TableCell align="right">Lot Size</TableCell>
                    <TableCell align="right">Tick Size</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {paginatedMappings.map((mapping) => (
                    <TableRow key={`${mapping.standard_symbol}-${mapping.broker_token}`}>
                      <TableCell>
                        <Typography variant="body2" fontWeight="medium">
                          {mapping.standard_symbol}
                        </Typography>
                      </TableCell>
                      <TableCell>{mapping.broker_symbol}</TableCell>
                      <TableCell>
                        <Typography variant="body2" sx={{ fontFamily: 'monospace' }}>
                          {mapping.broker_token}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip label={mapping.exchange} size="small" />
                      </TableCell>
                      <TableCell>
                        <Chip label={mapping.instrument_type} size="small" variant="outlined" />
                      </TableCell>
                      <TableCell align="right">{mapping.lot_size}</TableCell>
                      <TableCell align="right">{mapping.tick_size}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
            <TablePagination
              rowsPerPageOptions={[10, 25, 50, 100]}
              component="div"
              count={mappings.length}
              rowsPerPage={rowsPerPage}
              page={page}
              onPageChange={handleChangePage}
              onRowsPerPageChange={handleChangeRowsPerPage}
            />
          </>
        )}
      </Paper>

      {/* Validate Symbol Dialog */}
      <Dialog open={validateDialogOpen} onClose={handleCloseValidateDialog} maxWidth="sm" fullWidth>
        <DialogTitle>Validate Symbol</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Check if a symbol exists in the {selectedBroker} mapping
          </Typography>
          <TextField
            fullWidth
            label="Standard Symbol"
            value={validateSymbol}
            onChange={(e) => setValidateSymbol(e.target.value.toUpperCase())}
            placeholder="e.g., RELIANCE"
            sx={{ mb: 2 }}
            onKeyPress={(e) => {
              if (e.key === 'Enter') {
                handleValidateSymbol();
              }
            }}
          />

          {validationResult && (
            <Alert
              severity={validationResult.valid ? 'success' : 'error'}
              icon={validationResult.valid ? <CheckCircle /> : <ErrorIcon />}
            >
              {validationResult.valid ? (
                <Box>
                  <Typography variant="body2" fontWeight="medium">
                    Symbol is valid!
                  </Typography>
                  <Typography variant="caption" display="block" sx={{ mt: 0.5 }}>
                    Broker Token: {validationResult.broker_token}
                  </Typography>
                </Box>
              ) : (
                <Box>
                  <Typography variant="body2" fontWeight="medium">
                    Symbol not found
                  </Typography>
                  <Typography variant="caption" display="block" sx={{ mt: 0.5 }}>
                    {validationResult.error || `Symbol ${validateSymbol} is not mapped for ${selectedBroker}`}
                  </Typography>
                </Box>
              )}
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseValidateDialog}>Close</Button>
          <Button
            variant="contained"
            onClick={handleValidateSymbol}
            disabled={validating || !validateSymbol.trim()}
            startIcon={validating ? <CircularProgress size={20} /> : <Search />}
          >
            Validate
          </Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar for notifications */}
      <Snackbar
        open={snackbar.open}
        autoHideDuration={6000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert onClose={handleCloseSnackbar} severity={snackbar.severity} sx={{ width: '100%' }}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
}
