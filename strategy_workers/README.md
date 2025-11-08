# Strategy Execution Engine

This module implements the strategy execution engine for the multi-user algorithmic trading platform.

## Overview

The strategy execution engine manages the lifecycle of trading strategies, from loading and initialization to execution and error handling. It supports:

- **Pre-built strategy plugins** that implement the IStrategy interface
- **Multi-timeframe data aggregation** for strategy analysis
- **Real-time execution** on tick updates and candle completions
- **State persistence** in Redis for fault tolerance
- **Error handling and isolation** to prevent strategy failures from affecting the system
- **Concurrent strategy limits** to manage system resources

## Architecture

### Core Components

1. **Strategy Interface (`strategy_interface.py`)**
   - `IStrategy`: Abstract base class for all trading strategies
   - Data classes: `StrategyConfig`, `Signal`, `Candle`, `MultiTimeframeData`, etc.
   - Strategy lifecycle methods: `initialize()`, `on_tick()`, `on_candle_complete()`, `cleanup()`

2. **Strategy Plugin Manager (`strategy_plugin_manager.py`)**
   - Discovers and loads pre-built strategy plugins from the `strategies/` directory
   - Validates strategy parameters against configuration
   - Manages strategy metadata and configurations

3. **Strategy State Manager (`strategy_state_manager.py`)**
   - Persists strategy state in Redis for fault tolerance
   - Tracks active strategies and their status
   - Supports state recovery after service restarts

4. **Multi-Timeframe Data Provider (`multi_timeframe_provider.py`)**
   - Aggregates market data from multiple timeframes
   - Provides synchronized data to strategies
   - Ensures data consistency across timeframes

5. **Strategy Orchestrator (`strategy_orchestrator.py`)**
   - Manages strategy lifecycle (load, execute, pause, resume, stop)
   - Executes strategies on tick updates and candle completions
   - Validates trading signals before routing to order management
   - Handles strategy errors and implements isolation
   - Enforces concurrent strategy limits

## Pre-built Strategies

### Moving Average Crossover

A simple trend-following strategy based on moving average crossovers.

**Location**: `strategies/moving_average_crossover/`

**Parameters**:
- `fast_period`: Period for fast moving average (5-50)
- `slow_period`: Period for slow moving average (10-200)
- `ma_type`: Type of moving average (SMA or EMA)
- `confirmation_timeframe`: Optional higher timeframe for trend confirmation
- `quantity`: Quantity to trade per signal

**Entry Logic**:
- Long: Fast MA crosses above Slow MA
- Optional: Confirm with higher timeframe trend

**Exit Logic**:
- Fast MA crosses below Slow MA

## Creating a New Strategy

To create a new pre-built strategy:

1. Create a new directory under `strategies/` (e.g., `strategies/my_strategy/`)

2. Create `config.json` with strategy metadata:
```json
{
  "name": "My Strategy",
  "version": "1.0.0",
  "description": "Strategy description",
  "parameters": [
    {
      "name": "param_name",
      "type": "integer",
      "default": 10,
      "min": 5,
      "max": 50,
      "required": true,
      "description": "Parameter description"
    }
  ]
}
```

3. Create `strategy.py` implementing the `IStrategy` interface:
```python
from strategy_workers.strategy_interface import IStrategy, StrategyConfig, MultiTimeframeData, Candle, Signal
from typing import Optional

class MyStrategy(IStrategy):
    def initialize(self, config: StrategyConfig) -> None:
        # Initialize strategy with config
        pass
    
    def on_tick(self, data: MultiTimeframeData) -> Optional[Signal]:
        # Process tick updates (optional)
        return None
    
    def on_candle_complete(self, timeframe: str, candle: Candle, data: MultiTimeframeData) -> Optional[Signal]:
        # Process candle completions
        # Return Signal if conditions are met
        return None
    
    def cleanup(self) -> None:
        # Cleanup resources
        pass
```

4. The strategy will be automatically discovered on service startup

## Usage

### Loading a Strategy

```python
from strategy_workers.strategy_orchestrator import StrategyOrchestrator
from strategy_workers.strategy_interface import StrategyConfig, RiskConfig

config = StrategyConfig(
    strategy_id="unique-id",
    account_id="account-id",
    trading_mode="paper",  # or "live"
    symbols=["NIFTY", "BANKNIFTY"],
    timeframes=["1m", "5m"],
    parameters={
        "fast_period": 10,
        "slow_period": 20
    },
    risk_management=RiskConfig(
        max_position_size=100,
        stop_loss_percentage=2.0,
        trailing_stop_percentage=1.5
    )
)

orchestrator.load_strategy(config, "Moving Average Crossover")
```

### Executing on Market Data Updates

```python
# On tick update
signal = orchestrator.execute_on_tick(symbol="NIFTY", strategy_id="unique-id")

# On candle completion
signal = orchestrator.execute_on_candle_complete(
    symbol="NIFTY",
    timeframe="1m",
    candle=completed_candle,
    strategy_id="unique-id"
)

if signal:
    # Route signal to order management
    pass
```

### Managing Strategy Lifecycle

```python
# Pause a strategy
orchestrator.pause_strategy("unique-id")

# Resume a strategy
orchestrator.resume_strategy("unique-id")

# Stop a strategy
orchestrator.stop_strategy("unique-id")

# Pause all strategies for an account (e.g., loss limit breached)
orchestrator.pause_all_strategies("account-id", "Loss limit breached")
```

## Testing

Comprehensive unit tests are provided in `tests/test_strategy_execution.py`:

- Strategy plugin discovery and loading
- Parameter validation
- State persistence and recovery
- Multi-timeframe data aggregation
- Strategy execution and signal generation
- Error handling and isolation
- Moving Average Crossover strategy logic

Run tests:
```bash
python3 -m pytest tests/test_strategy_execution.py -v
```

## Requirements Addressed

This implementation addresses the following requirements:

- **Requirement 3.1**: Pre-built strategy library with plugin architecture
- **Requirement 3.2**: Strategy configuration through parameters
- **Requirement 3.4**: Paper trading and live trading mode support
- **Requirement 3.5**: Strategy pause/resume functionality
- **Requirement 9.3**: Multi-timeframe data processing
- **Requirement 9.4**: Historical and forming candle access
- **Requirement 12.2**: Concurrent strategy limit enforcement
- **Requirement 12.4**: Strategy error handling and isolation
- **Requirement 12.5**: Strategy state management
- **Requirement 13.3**: Symbol mapping integration (via order router)

## Future Enhancements

- Additional pre-built strategies (RSI, MACD, Bollinger Bands, etc.)
- Strategy backtesting integration
- Performance metrics tracking per strategy
- Strategy optimization and parameter tuning
- Machine learning-based strategies
- Portfolio-level strategy coordination
