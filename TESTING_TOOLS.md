# Testing Tools and Utilities

This document describes the testing tools and utilities available for offline development and testing.

## Overview

The platform provides comprehensive testing tools for:
- Running strategies in replay mode without UI
- Validating data quality
- Generating mock data for edge cases
- Debugging strategies
- Performance profiling

## Replay CLI Tool

Run strategies against historical data from the command line.

### Usage

```bash
# Run single replay
python scripts/replay_cli.py run \
  --data replay_data/RELIANCE_20240101_20240131.csv \
  --strategy strategy_config.json \
  --speed 10.0 \
  --output results.json

# Run batch of tests
python scripts/replay_cli.py batch --config batch_config.json

# List saved sessions
python scripts/replay_cli.py list
```

### Strategy Config Format

```json
{
  "strategy_id": "ma_crossover",
  "symbols": ["RELIANCE", "TCS"],
  "timeframes": ["1m", "5m"],
  "parameters": {
    "fast_period": 10,
    "slow_period": 20
  }
}
```

### Batch Config Format

```json
{
  "tests": [
    {
      "name": "MA Crossover - Trending Market",
      "data_files": [
        "replay_data/RELIANCE_trending.csv"
      ],
      "strategy": {
        "strategy_id": "ma_crossover",
        "symbols": ["RELIANCE"],
        "parameters": {
          "fast_period": 10,
          "slow_period": 20
        }
      },
      "speed": 10.0,
      "output_file": "results/ma_crossover_trending.json"
    },
    {
      "name": "MA Crossover - Ranging Market",
      "data_files": [
        "replay_data/RELIANCE_ranging.csv"
      ],
      "strategy": {
        "strategy_id": "ma_crossover",
        "symbols": ["RELIANCE"],
        "parameters": {
          "fast_period": 10,
          "slow_period": 20
        }
      },
      "speed": 10.0,
      "output_file": "results/ma_crossover_ranging.json"
    }
  ]
}
```

## Data Quality Checker

Validate historical data completeness and quality.

### Usage

```bash
# Check single file
python scripts/data_quality_checker.py replay_data/RELIANCE_20240101.csv

# Check all files in directory
python scripts/data_quality_checker.py replay_data/

# Show summary only
python scripts/data_quality_checker.py replay_data/ --summary
```

### What It Checks

- **Completeness**: Detects gaps in data
- **Data Integrity**: Validates price relationships (high >= low, etc.)
- **Consistency**: Finds duplicate timestamps
- **Format**: Checks for missing fields
- **Quality Score**: 0-100 score based on issues found

### Example Output

```
================================================================================
Data Quality Report: replay_data/RELIANCE_20240101.csv
================================================================================
Symbol: RELIANCE
Records: 375
Time Range: 2024-01-01 09:15:00 to 2024-01-01 15:30:00
Duration: 6.25 hours

Quality Score: 95.0/100

Issues Found:
  - 2 gaps found (max gap: 120.0 seconds)
  - 1 duplicate timestamps

Top 5 Largest Gaps:
  - 2024-01-01 11:30:00 to 2024-01-01 11:32:00 (120.0 seconds)
  - 2024-01-01 14:15:00 to 2024-01-01 14:16:00 (60.0 seconds)
```

## Mock Data Generator

Generate mock market data for edge case testing.

### Usage

```bash
# Generate all types of test data
python scripts/mock_data_generator.py \
  --symbol TEST \
  --price 1000 \
  --candles 1000 \
  --output-dir test_data \
  --type all

# Generate specific type
python scripts/mock_data_generator.py \
  --symbol TEST \
  --price 1000 \
  --candles 1000 \
  --type flash_crash
```

### Edge Case Types

1. **Normal**: Standard market data with typical volatility
2. **Gaps**: Data with missing periods (simulates connection issues)
3. **Circuit Breaker**: 10% drop followed by trading halt
4. **Extreme Volatility**: High volatility with large price swings
5. **Flash Crash**: Sudden 20% drop with immediate recovery

### Example

```bash
# Generate flash crash scenario
python scripts/mock_data_generator.py \
  --symbol RELIANCE \
  --price 2500 \
  --candles 500 \
  --type flash_crash

# Output: test_data/RELIANCE_flash_crash_20240115.csv
```

## Historical Data Downloader

Download real historical data from Angel One SmartAPI.

### Usage

```bash
# Download with credentials
python scripts/download_historical_data.py \
  --days 30 \
  --symbols RELIANCE TCS INFY \
  --api-key YOUR_API_KEY \
  --client-code YOUR_CLIENT_CODE \
  --password YOUR_PASSWORD \
  --totp YOUR_TOTP

# Generate mock data if no credentials
python scripts/download_historical_data.py \
  --days 30 \
  --symbols RELIANCE TCS INFY \
  --output-dir replay_data
```

### Output

Creates CSV files in format: `{SYMBOL}_{START_DATE}_{END_DATE}.csv`

Example: `RELIANCE_20240101_20240131.csv`

## Strategy Debugger

Debug strategies with breakpoints and variable inspection.

### API Endpoints

```bash
# Add breakpoint on candle completion
curl -X POST http://localhost:8000/api/dev/debugger/breakpoints \
  -H "Content-Type: application/json" \
  -d '{
    "type": "candle_complete",
    "condition": "close_price > 2500"
  }'

# Pause debugger
curl -X POST http://localhost:8000/api/dev/debugger/pause

# Resume debugger
curl -X POST http://localhost:8000/api/dev/debugger/resume

# Step to next event
curl -X POST http://localhost:8000/api/dev/debugger/step

# Get current frame
curl http://localhost:8000/api/dev/debugger/frames/current
```

### Breakpoint Types

- `candle_complete`: Break when candle completes
- `signal_generated`: Break when strategy generates signal
- `order_placed`: Break when order is placed
- `position_opened`: Break when position opens
- `position_closed`: Break when position closes
- `indicator_value`: Break on indicator condition

### Conditional Breakpoints

```python
# Break when RSI crosses above 70
{
  "type": "indicator_value",
  "condition": "rsi > 70"
}

# Break when price drops 2%
{
  "type": "candle_complete",
  "condition": "close_price < entry_price * 0.98"
}
```

## Variable Inspector

Monitor strategy variables and indicators in real-time.

### API Endpoints

```bash
# Watch a variable
curl -X POST http://localhost:8000/api/dev/inspector/watch/variable \
  -H "Content-Type: application/json" \
  -d '{"name": "position_size"}'

# Watch an indicator
curl -X POST http://localhost:8000/api/dev/inspector/watch/indicator \
  -H "Content-Type: application/json" \
  -d '{"name": "sma_20"}'

# Get current values
curl http://localhost:8000/api/dev/inspector/values

# Get variable history
curl http://localhost:8000/api/dev/inspector/history/variable/position_size?limit=100
```

### Example Response

```json
{
  "success": true,
  "values": {
    "variables": {
      "position_size": 100,
      "entry_price": 2500.50,
      "stop_loss": 2450.00
    },
    "indicators": {
      "sma_20": 2485.30,
      "rsi_14": 65.5,
      "macd": 12.5
    }
  }
}
```

## Market Condition Simulator

Simulate different market conditions for testing.

### Usage

```python
from market_data_engine.market_condition_simulator import (
    MarketConditionSimulator,
    MarketCondition
)

simulator = MarketConditionSimulator()

# Set market condition
simulator.set_condition(MarketCondition.TRENDING_UP)

# Generate ticks
ticks = simulator.generate_ticks(
    symbol="RELIANCE",
    start_price=2500.0,
    num_ticks=1000
)
```

### Market Conditions

- `TRENDING_UP`: Strong upward trend
- `TRENDING_DOWN`: Strong downward trend
- `RANGING`: Sideways movement
- `VOLATILE`: High volatility
- `QUIET`: Low volatility
- `BREAKOUT`: Consolidation then breakout
- `REVERSAL`: Trend reversal

## Automated Test Suite

Run automated tests for strategy validation.

### Usage

```bash
# Run all tests
pytest tests/ -v

# Run specific test category
pytest tests/test_strategy_execution.py -v

# Run with coverage
pytest tests/ --cov=. --cov-report=html

# Run only fast tests
pytest tests/ -v -m "not slow"
```

### Test Categories

- Unit tests: Individual component testing
- Integration tests: Multi-component testing
- End-to-end tests: Full workflow testing
- Performance tests: Load and stress testing

## Performance Profiler

Profile strategy execution performance.

### Usage

```python
import cProfile
import pstats

# Profile strategy execution
profiler = cProfile.Profile()
profiler.enable()

# Run strategy
strategy.execute()

profiler.disable()

# Print stats
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)
```

### Metrics

- Execution time per function
- Number of calls
- Cumulative time
- Memory usage

## Best Practices

### 1. Data Quality

Always check data quality before running tests:

```bash
python scripts/data_quality_checker.py replay_data/ --summary
```

### 2. Edge Case Testing

Test strategies against all edge cases:

```bash
# Generate all edge cases
python scripts/mock_data_generator.py --type all

# Run strategy against each
for file in test_data/*.csv; do
  python scripts/replay_cli.py run --data $file --strategy config.json
done
```

### 3. Debugging Workflow

1. Add breakpoints at key points
2. Watch important variables
3. Step through execution
4. Inspect state at each step
5. Fix issues and repeat

### 4. Performance Testing

1. Profile strategy execution
2. Identify bottlenecks
3. Optimize hot paths
4. Verify improvements

### 5. Continuous Testing

Integrate tests into CI/CD:

```yaml
# .github/workflows/test.yml
- name: Run tests
  run: |
    python scripts/data_quality_checker.py replay_data/
    pytest tests/ -v --cov=.
```

## Troubleshooting

### Data Quality Issues

```bash
# Check data quality
python scripts/data_quality_checker.py replay_data/

# Regenerate if needed
python scripts/download_historical_data.py --days 30
```

### Replay Not Starting

```bash
# Check simulator status
curl http://localhost:8002/api/replay/control/status

# Check loaded data
curl http://localhost:8002/api/replay/control/status | jq '.status.loaded_symbols'
```

### Debugger Not Pausing

```bash
# Check breakpoints
curl http://localhost:8000/api/dev/debugger/breakpoints

# Verify condition syntax
# Conditions must be valid Python expressions
```

## Support

For issues or questions:
1. Check logs: `docker-compose logs -f`
2. Review this guide
3. Check TESTING_ENVIRONMENT.md
4. Contact development team
