#!/usr/bin/env python3
"""
Simple documentation viewer for the Trading Platform.
Shows API endpoints, architecture, and system information.
"""
import os
import sys
from pathlib import Path

def print_header(title):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")

def print_section(title):
    """Print a section title."""
    print(f"\n{title}")
    print("-" * len(title))

def show_api_endpoints():
    """Show available API endpoints."""
    print_header("API ENDPOINTS")
    
    endpoints = {
        "Authentication": [
            ("POST", "/api/auth/register", "Register new user"),
            ("POST", "/api/auth/login", "Login user"),
            ("POST", "/api/auth/logout", "Logout user"),
            ("GET", "/api/auth/me", "Get current user info"),
        ],
        "Positions": [
            ("GET", "/api/positions", "Get all positions"),
            ("GET", "/api/positions/<id>", "Get position by ID"),
            ("POST", "/api/positions/<id>/close", "Close position"),
            ("PUT", "/api/positions/<id>/trailing-stop", "Configure trailing stop"),
        ],
        "Orders": [
            ("GET", "/api/orders", "Get all orders"),
            ("POST", "/api/orders", "Submit new order"),
            ("DELETE", "/api/orders/<id>", "Cancel order"),
        ],
        "Strategies": [
            ("GET", "/api/strategies", "List available strategies"),
            ("POST", "/api/strategies/activate", "Activate strategy"),
            ("POST", "/api/strategies/<id>/pause", "Pause strategy"),
            ("POST", "/api/strategies/<id>/resume", "Resume strategy"),
        ],
        "Risk Management": [
            ("GET", "/api/risk/limits", "Get loss limits"),
            ("PUT", "/api/risk/limits", "Update loss limits"),
            ("GET", "/api/risk/metrics", "Get risk metrics"),
        ],
        "Analytics": [
            ("GET", "/api/analytics/performance", "Get performance metrics"),
            ("GET", "/api/analytics/trades", "Get trade history"),
            ("GET", "/api/analytics/equity-curve", "Get equity curve data"),
        ],
    }
    
    for category, eps in endpoints.items():
        print_section(category)
        for method, path, description in eps:
            print(f"  {method:6} {path:40} - {description}")

def show_architecture():
    """Show system architecture."""
    print_header("SYSTEM ARCHITECTURE")
    
    print("""
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React)                         │
│                      http://localhost:3000                       │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API GATEWAY (Flask)                         │
│                      http://localhost:5000                       │
│  - Authentication  - Positions  - Orders  - Risk Management     │
└──┬────────┬─────────┬──────────┬──────────┬──────────┬─────────┘
   │        │         │          │          │          │
   ▼        ▼         ▼          ▼          ▼          ▼
┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────────┐
│WebSkt│ │Market│ │Order │ │Strat │ │Analyt│ │Database  │
│Svc   │ │Data  │ │Proc  │ │Work  │ │Svc   │ │PostgreSQL│
│:5001 │ │Engine│ │:8003 │ │:8004 │ │:5002 │ │:5432     │
└──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────────┘
    │        │         │        │        │          │
    └────────┴─────────┴────────┴────────┴──────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │   Redis (Cache)      │
              │   :6379              │
              └──────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │   InfluxDB (TSDB)    │
              │   :8086              │
              └──────────────────────┘
""")

def show_trailing_stop_docs():
    """Show trailing stop-loss documentation."""
    print_header("TRAILING STOP-LOSS FEATURE")
    
    print("""
OVERVIEW
--------
Trailing stop-loss automatically adjusts the stop price as the market moves
in your favor, locking in profits while limiting losses.

HOW IT WORKS
------------
Long Position:
  - Stop price = Highest Price × (1 - Percentage)
  - Stop only moves UP, never down
  - Triggered when: Current Price ≤ Stop Price

Short Position:
  - Stop price = Lowest Price × (1 + Percentage)
  - Stop only moves DOWN, never up
  - Triggered when: Current Price ≥ Stop Price

CONFIGURATION
-------------
Percentage Range: 0.1% to 10% (0.001 to 0.1)

Example:
  Entry Price: ₹2450
  Trailing Stop: 2%
  Initial Stop: ₹2401 (2450 × 0.98)
  
  Price moves to ₹2500:
    New Stop: ₹2450 (2500 × 0.98) ✓ Updated
  
  Price drops to ₹2480:
    Stop remains: ₹2450 (doesn't move down)
  
  Price drops to ₹2449:
    STOP TRIGGERED! Exit order generated automatically

API USAGE
---------
Configure trailing stop:
  PUT /api/positions/<position_id>/trailing-stop
  Body: {
    "percentage": 0.02,  // 2%
    "current_price": 2450.00
  }

Disable trailing stop:
  DELETE /api/positions/<position_id>/trailing-stop

AUTOMATIC BEHAVIOR
------------------
✓ Stop price updates automatically on every price tick
✓ Exit order generated immediately when stop is triggered
✓ Notification sent to user
✓ Works in both paper and live trading modes
✓ Separate tracking per trading mode

IMPLEMENTATION
--------------
Files:
  - order_processor/trailing_stop_manager.py
  - order_processor/trailing_stop_order_handler.py
  - order_processor/market_data_processor.py
  - api_gateway/position_routes.py

Tests:
  - tests/test_trailing_stop_smoke.py (9 tests)
  - tests/test_trailing_stop_integration.py (8 tests)
  - Status: ✅ 17/17 PASSING
""")

def show_quick_start():
    """Show quick start guide."""
    print_header("QUICK START GUIDE")
    
    print("""
1. INSTALLATION
   ./install.sh

2. START SERVICES
   ./run.sh

3. ACCESS APPLICATION
   Frontend:  http://localhost:3000
   API:       http://localhost:5000
   WebSocket: http://localhost:5001
   Analytics: http://localhost:5002

4. RUN TESTS
   ./test.sh

5. CHECK STATUS
   ./status.sh

6. STOP SERVICES
   ./stop.sh

DEVELOPMENT WORKFLOW
--------------------
# Start in development mode
./run.sh development

# View logs
tail -f logs/api_gateway.log
tail -f logs/order_processor.log

# Run specific tests
./test.sh trailing-stop

# Check service status
./status.sh

CONFIGURATION
-------------
Edit .env.development for local settings:
  - Database connection
  - Redis connection
  - Service ports
  - API keys (for live trading)

DOCUMENTATION
-------------
  - README.md - Project overview
  - SCRIPTS_GUIDE.md - Detailed script documentation
  - QUICK_START.md - Quick reference
  - TEST_STATUS.md - Test results and coverage
  - API_POSITION_ENDPOINTS.md - API documentation
""")

def show_project_structure():
    """Show project structure."""
    print_header("PROJECT STRUCTURE")
    
    print("""
trading-platform/
├── api_gateway/          # REST API endpoints
├── websocket_service/    # Real-time WebSocket updates
├── market_data_engine/   # Market data processing
├── order_processor/      # Order execution & positions
│   ├── trailing_stop_manager.py        ✓ Implemented
│   ├── trailing_stop_order_handler.py  ✓ Implemented
│   └── market_data_processor.py        ✓ Implemented
├── strategy_workers/     # Strategy execution
├── analytics_service/    # Analytics & reporting
├── backtesting_engine/   # Backtesting system
├── frontend/             # React frontend
├── shared/               # Shared models & utilities
├── tests/                # Test suite
│   ├── test_trailing_stop_smoke.py     ✓ 9 tests passing
│   └── test_trailing_stop_integration.py ✓ 8 tests passing
├── scripts/              # Utility scripts
├── alembic/              # Database migrations
├── logs/                 # Service logs
├── install.sh            # Installation script
├── run.sh                # Start services
├── stop.sh               # Stop services
├── test.sh               # Run tests
└── status.sh             # Check status
""")

def show_menu():
    """Show interactive menu."""
    while True:
        print_header("TRADING PLATFORM - DOCUMENTATION VIEWER")
        print("1. API Endpoints")
        print("2. System Architecture")
        print("3. Trailing Stop-Loss Feature")
        print("4. Quick Start Guide")
        print("5. Project Structure")
        print("6. View All")
        print("0. Exit")
        print()
        
        choice = input("Select option (0-6): ").strip()
        
        if choice == "1":
            show_api_endpoints()
        elif choice == "2":
            show_architecture()
        elif choice == "3":
            show_trailing_stop_docs()
        elif choice == "4":
            show_quick_start()
        elif choice == "5":
            show_project_structure()
        elif choice == "6":
            show_api_endpoints()
            show_architecture()
            show_trailing_stop_docs()
            show_quick_start()
            show_project_structure()
        elif choice == "0":
            print("\nGoodbye!\n")
            break
        else:
            print("\nInvalid option. Please try again.")
        
        input("\nPress Enter to continue...")

if __name__ == "__main__":
    try:
        show_menu()
    except KeyboardInterrupt:
        print("\n\nGoodbye!\n")
        sys.exit(0)
