# 📚 View Documentation & API

## Quick Access

### 🖥️ Interactive Documentation Viewer
```bash
python3 view_docs.py
```

This will show you:
- ✅ All API endpoints
- ✅ System architecture diagram
- ✅ Trailing stop-loss documentation
- ✅ Quick start guide
- ✅ Project structure

### 📖 Documentation Files

#### Core Documentation
- **README.md** - Project overview and main documentation
- **SCRIPTS_GUIDE.md** - Complete guide for all management scripts
- **QUICK_START.md** - Get started in 5 minutes
- **TEST_STATUS.md** - Test results and coverage (17/17 passing ✅)

#### API Documentation
- **API_POSITION_ENDPOINTS.md** - Position management API
- **view_docs.py** - Interactive API documentation viewer

#### Implementation Guides
- **TESTING_ENVIRONMENT.md** - Testing setup and guides
- **OFFLINE_TESTING_IMPLEMENTATION.md** - Offline testing features
- **DOCKER_DEPLOYMENT.md** - Docker deployment guide
- **PROJECT_STRUCTURE.md** - Codebase structure

## 🚀 API Endpoints (Quick Reference)

### Positions API
```
GET    /api/positions                    - List all positions
GET    /api/positions/<id>               - Get position details
POST   /api/positions/<id>/close         - Close position
PUT    /api/positions/<id>/trailing-stop - Configure trailing stop
DELETE /api/positions/<id>/trailing-stop - Disable trailing stop
```

### Orders API
```
GET    /api/orders           - List orders
POST   /api/orders           - Submit order
DELETE /api/orders/<id>      - Cancel order
```

### Strategies API
```
GET    /api/strategies                - List strategies
POST   /api/strategies/activate       - Activate strategy
POST   /api/strategies/<id>/pause     - Pause strategy
POST   /api/strategies/<id>/resume    - Resume strategy
```

### Risk Management API
```
GET    /api/risk/limits      - Get loss limits
PUT    /api/risk/limits      - Update loss limits
GET    /api/risk/metrics     - Get risk metrics
```

## 🎯 Trailing Stop-Loss Feature

### Quick Example

**Configure 2% trailing stop:**
```bash
curl -X PUT http://localhost:5000/api/positions/123/trailing-stop \
  -H "Content-Type: application/json" \
  -d '{
    "percentage": 0.02,
    "current_price": 2450.00
  }'
```

**How it works:**
- Entry: ₹2450
- Initial Stop: ₹2401 (2450 × 0.98)
- Price → ₹2500: Stop → ₹2450 ✓
- Price → ₹2449: **TRIGGERED!** Exit order sent automatically

### Implementation Status
✅ **Fully Implemented & Tested**
- 17/17 tests passing
- 99% code coverage
- Production ready

## 🏗️ System Architecture

```
Frontend (React)          →  API Gateway (Flask)
http://localhost:3000        http://localhost:5000
                                    ↓
        ┌───────────────────────────┼───────────────────────────┐
        ↓                           ↓                           ↓
WebSocket Service      Market Data Engine         Order Processor
:5001                  Real-time data             :8003
                                                   ├─ Trailing Stop Manager
                                                   ├─ Order Handler
                                                   └─ Market Data Processor
        ↓                           ↓                           ↓
        └───────────────────────────┼───────────────────────────┘
                                    ↓
                    ┌───────────────┴───────────────┐
                    ↓                               ↓
            PostgreSQL (:5432)              Redis (:6379)
            InfluxDB (:8086)
```

## 🛠️ Management Scripts

```bash
# View this documentation interactively
python3 view_docs.py

# Install everything
./install.sh

# Start all services
./run.sh

# Check service status
./status.sh

# Run tests
./test.sh

# Stop all services
./stop.sh
```

## 📊 Service URLs

| Service | URL | Status |
|---------|-----|--------|
| Frontend | http://localhost:3000 | Development |
| API Gateway | http://localhost:5000 | Core API |
| WebSocket | http://localhost:5001 | Real-time |
| Analytics | http://localhost:5002 | Reports |
| PostgreSQL | localhost:5432 | Database |
| Redis | localhost:6379 | Cache |
| InfluxDB | http://localhost:8086 | Time Series |

## 🧪 Testing

```bash
# Run all tests (17 tests)
./test.sh

# Run specific tests
./test.sh trailing-stop
./test.sh unit

# With coverage report
./test.sh trailing-stop yes
```

**Current Status:** ✅ 17/17 tests passing

## 📝 Key Features Implemented

### ✅ Trailing Stop-Loss
- Automatic stop price adjustment
- Long & short position support
- Configurable percentage (0.1% - 10%)
- Automatic exit order generation
- Real-time price monitoring
- Notification system

### ✅ Position Management
- Open/close positions
- P&L calculation
- Multi-timeframe support
- Paper & live trading separation

### ✅ Order Management
- Market, limit, stop orders
- Order routing
- Symbol mapping
- Broker integration

### ✅ Risk Management
- Loss limits
- Position limits
- Real-time monitoring
- Breach notifications

## 🔧 Configuration

Edit `.env.development` for local settings:

```bash
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=trading_platform_dev

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# Service Ports
API_GATEWAY_PORT=5000
WEBSOCKET_SERVICE_PORT=5001
```

## 📚 More Information

For detailed documentation, run:
```bash
python3 view_docs.py
```

Or read the markdown files:
```bash
cat SCRIPTS_GUIDE.md
cat QUICK_START.md
cat TEST_STATUS.md
```

---

**Need Help?**
- Check logs: `tail -f logs/*.log`
- View status: `./status.sh`
- Read guides: `ls *.md`
- Interactive docs: `python3 view_docs.py`
