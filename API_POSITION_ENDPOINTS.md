# Position Management API Endpoints

## Overview
This document provides a quick reference for all position management API endpoints implemented in task 9.4

---

## Endpoints

### 1. Get Account Positions
**Endpoint:** `GET /api/positions/account/<account_id>`

**Authentication:** Required (JWT)

**Roles:** Trader, Investor

**Query Parameters:**
- `trading_mode` (optional): Filter by 'paper' or 'live'
- `include_closed` (optional): Include closed positions (default: false)

**Example Request:**
```bash
GET /api/positions/account/123e4567-e89b-12d3-a456-426614174000?trading_mode=paper
Authorization: Bearer <jwt_token>
```

**Example Response:**
```json
{
  "positions": [
    {
      "id": "uuid",
      "symbol": "RELIANCE",
      "side": "long",
      "quantity": 10,
      "entry_price": 2450.00,
      "current_price": 2500.00,
      "unrealized_pnl": 500.00,
      "realized_pnl": 0.00,
      "trading_mode": "paper",
      "stop_loss": 2400.00,
      "take_profit": 2600.00,
      "trailing_stop_loss": {
        "enabled": true,
        "percentage": 0.02,
        "current_stop_price": 2450.00
      },
      "opened_at": "2024-01-01T10:00:00",
      "closed_at": null
    }
  ]
}
```

---

### 2. Get Single Position
**Endpoint:** `GET /api/positions/<position_id>`

**Authentication:** Required (JWT)

**Roles:** Trader, Investor

**Example Request:**
```bash
GET /api/positions/123e4567-e89b-12d3-a456-426614174000
Authorization: Bearer <jwt_token>
```

**Example Response:**
```json
{
  "id": "uuid",
  "account_id": "uuid",
  "strategy_id": "uuid",
  "symbol": "RELIANCE",
  "side": "long",
  "quantity": 10,
  "entry_price": 2450.00,
  "current_price": 2500.00,
  "unrealized_pnl": 500.00,
  "realized_pnl": 0.00,
  "trading_mode": "paper",
  "stop_loss": 2400.00,
  "take_profit": 2600.00,
  "trailing_stop_loss": {
    "enabled": true,
    "percentage": 0.02,
    "current_stop_price": 2450.00,
    "highest_price": 2500.00,
    "lowest_price": 2400.00
  },
  "opened_at": "2024-01-01T10:00:00",
  "closed_at": null
}
```

---

### 3. Close Position
**Endpoint:** `POST /api/positions/<position_id>/close`

**Authentication:** Required (JWT)

**Roles:** Trader only

**Request Body:**
```json
{
  "closing_price": 2460.00,
  "commission": 10.00
}
```

**Example Request:**
```bash
POST /api/positions/123e4567-e89b-12d3-a456-426614174000/close
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "closing_price": 2460.00,
  "commission": 10.00
}
```

**Example Response:**
```json
{
  "message": "Position closed successfully",
  "position_id": "uuid",
  "realized_pnl": 485.30
}
```

---

### 4. Update Trailing Stop-Loss
**Endpoint:** `PUT /api/positions/<position_id>/trailing-stop`

**Authentication:** Required (JWT)

**Roles:** Trader only

**Request Body:**
```json
{
  "percentage": 0.02,
  "current_price": 2450.00
}
```

**Example Request:**
```bash
PUT /api/positions/123e4567-e89b-12d3-a456-426614174000/trailing-stop
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "percentage": 0.02,
  "current_price": 2450.00
}
```

**Example Response:**
```json
{
  "message": "Trailing stop updated successfully",
  "trailing_stop": {
    "enabled": true,
    "percentage": 0.02,
    "current_stop_price": 2401.00
  }
}
```

**Validation:**
- Percentage must be between 0.001 (0.1%) and 0.1 (10%)

---

### 5. Get Risk Metrics
**Endpoint:** `GET /api/positions/risk-metrics/<account_id>`

**Authentication:** Required (JWT)

**Roles:** Trader, Investor

**Query Parameters:**
- `trading_mode` (optional): Filter by 'paper' or 'live'

**Example Request:**
```bash
GET /api/positions/risk-metrics/123e4567-e89b-12d3-a456-426614174000?trading_mode=live
Authorization: Bearer <jwt_token>
```

**Example Response:**
```json
{
  "total_exposure": 50000.00,
  "long_exposure": 35000.00,
  "short_exposure": 15000.00,
  "margin_utilization": 50000.00,
  "total_unrealized_pnl": 1500.00,
  "total_realized_pnl": 500.00,
  "total_pnl": 2000.00,
  "position_count": 5,
  "trading_mode": "live"
}
```

---

### 6. Get Position History
**Endpoint:** `GET /api/positions/history/<account_id>`

**Authentication:** Required (JWT)

**Roles:** Trader, Investor

**Query Parameters:**
- `trading_mode` (optional): Filter by 'paper' or 'live'
- `start_date` (optional): Start date in ISO format (e.g., "2024-01-01T00:00:00")
- `end_date` (optional): End date in ISO format
- `symbol` (optional): Filter by symbol (e.g., "RELIANCE")
- `limit` (optional): Maximum number of positions (default: 100)

**Example Request:**
```bash
GET /api/positions/history/123e4567-e89b-12d3-a456-426614174000?trading_mode=paper&start_date=2024-01-01T00:00:00&end_date=2024-01-31T23:59:59&limit=50
Authorization: Bearer <jwt_token>
```

**Example Response:**
```json
{
  "positions": [
    {
      "id": "uuid",
      "symbol": "TCS",
      "side": "long",
      "quantity": 5,
      "entry_price": 3500.00,
      "realized_pnl": 250.00,
      "trading_mode": "paper",
      "opened_at": "2024-01-15T10:00:00",
      "closed_at": "2024-01-20T15:30:00"
    }
  ],
  "count": 1
}
```

---

## Error Responses

### 400 Bad Request
```json
{
  "error": "Missing required field: closing_price"
}
```

### 403 Forbidden
```json
{
  "error": "Access denied to account"
}
```

### 404 Not Found
```json
{
  "error": "Position not found"
}
```

### 500 Internal Server Error
```json
{
  "error": "Failed to get positions"
}
```

---

## Security

All endpoints implement:
- JWT authentication via `@require_auth` decorator
- Role-based access control via `@require_role` decorator
- Account access verification
- Investor users have read-only access
- Trader users have full access to their account positions

---

## Notes

1. **Trading Mode Separation**: All endpoints support filtering by trading mode (paper/live) to maintain clear separation between simulated and real trading.

2. **Real-time Updates**: Position data includes current prices and unrealized P&L calculated in real-time.

3. **Trailing Stop-Loss**: Trailing stop configuration is included in position responses when enabled.

4. **Access Control**: Investors can view positions but cannot close them or modify trailing stops.

5. **Performance**: Position history queries are optimized with database indexes and support pagination via the `limit` parameter.
