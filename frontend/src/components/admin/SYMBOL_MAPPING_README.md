# Symbol Mapping Admin UI

## Overview

The Symbol Mapping Manager provides an admin interface for uploading and managing symbol mappings for different brokers. This ensures that standard NSE symbols can be correctly translated to broker-specific tokens.

## Features

### 1. CSV Upload
- Upload symbol mapping CSV files for different brokers
- Validation feedback showing successful and failed imports
- Error messages for invalid CSV format or data

### 2. Symbol Mapping Table
- View all symbol mappings for a selected broker
- Paginated table with 10/25/50/100 rows per page
- Displays:
  - Standard Symbol (e.g., RELIANCE)
  - Broker Symbol (e.g., RELIANCE-EQ)
  - Broker Token (e.g., 2885)
  - Exchange (NSE, BSE, NFO, MCX)
  - Instrument Type (EQ, FUT, OPT)
  - Lot Size
  - Tick Size

### 3. Symbol Validation
- Validate if a symbol exists in the mapping
- Returns broker token if symbol is found
- Shows error notification if symbol is missing

### 4. Missing Symbol Error Notifications
- Real-time notifications for validation results
- Success/error alerts with detailed messages
- Auto-dismiss after 6 seconds

## CSV Format

The CSV file must follow this format:

```csv
standard_symbol,broker_symbol,broker_token,exchange,instrument_type,lot_size,tick_size
RELIANCE,RELIANCE-EQ,2885,NSE,EQ,1,0.05
TCS,TCS-EQ,11536,NSE,EQ,1,0.05
INFY,INFY-EQ,1594,NSE,EQ,1,0.05
```

### Column Descriptions:
- **standard_symbol**: Standard NSE symbol (e.g., RELIANCE)
- **broker_symbol**: Broker-specific symbol format (e.g., RELIANCE-EQ)
- **broker_token**: Unique token used by broker API (e.g., 2885)
- **exchange**: Trading exchange (NSE, BSE, NFO, MCX)
- **instrument_type**: Type of instrument (EQ, FUT, OPT)
- **lot_size**: Minimum trading quantity (usually 1 for equity)
- **tick_size**: Minimum price movement (usually 0.05 for NSE)

## Usage

### Uploading Mappings

1. Navigate to Admin Dashboard → Symbol Mappings tab
2. Select the broker from the dropdown
3. Click "Choose CSV File" and select your mapping file
4. Click "Upload" to import the mappings
5. Review the upload result showing successful and failed imports

### Validating Symbols

1. Click "Validate Symbol" button
2. Enter the standard symbol (e.g., RELIANCE)
3. Click "Validate" to check if the symbol exists
4. View the broker token if found, or error message if not found

### Viewing Mappings

1. Select a broker from the dropdown
2. View the table of all mappings
3. Use pagination controls to navigate through large datasets
4. Click "Refresh" to reload the mappings

## API Endpoints Used

- `POST /api/symbol-mappings/upload` - Upload CSV file
- `GET /api/symbol-mappings/{broker_name}` - Get all mappings for a broker
- `GET /api/symbol-mappings/{broker_name}/{symbol}/validate` - Validate a symbol

## Requirements Addressed

- **Requirement 13.5**: Admin endpoint to upload symbol mapping CSV files
- **Requirement 13.6**: Missing symbol error handling and notifications

## Implementation Details

### Component Location
- `frontend/src/components/admin/SymbolMappingManager.tsx`

### State Management
- Local component state for mappings, loading, and validation
- No Redux integration needed (admin-only feature)

### Error Handling
- Upload validation errors displayed inline
- Symbol validation errors shown in dialog and snackbar
- Network errors caught and displayed to user

### User Experience
- Loading indicators during async operations
- Success/error feedback for all actions
- Helpful CSV format guide displayed on page
- Responsive table with pagination for large datasets
