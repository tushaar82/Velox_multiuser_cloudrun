"""
Configuration Modes for Testing and Development

Provides configuration profiles for different operating modes:
- live: Real market data and broker connections
- paper: Real market data with simulated trading
- replay: Historical data replay for testing
- simulated: Synthetic data generation for development
"""
from enum import Enum
from dataclasses import dataclass
from typing import Optional
import os


class OperatingMode(Enum):
    """System operating modes"""
    LIVE = "live"
    PAPER = "paper"
    REPLAY = "replay"
    SIMULATED = "simulated"


@dataclass
class ModeConfig:
    """Configuration for a specific operating mode"""
    mode: OperatingMode
    use_real_broker: bool
    use_real_market_data: bool
    enable_order_execution: bool
    enable_notifications: bool
    log_level: str
    description: str


# Mode configurations
MODE_CONFIGS = {
    OperatingMode.LIVE: ModeConfig(
        mode=OperatingMode.LIVE,
        use_real_broker=True,
        use_real_market_data=True,
        enable_order_execution=True,
        enable_notifications=True,
        log_level="INFO",
        description="Production mode with real trading"
    ),
    OperatingMode.PAPER: ModeConfig(
        mode=OperatingMode.PAPER,
        use_real_broker=False,
        use_real_market_data=True,
        enable_order_execution=False,
        enable_notifications=True,
        log_level="INFO",
        description="Paper trading with real market data"
    ),
    OperatingMode.REPLAY: ModeConfig(
        mode=OperatingMode.REPLAY,
        use_real_broker=False,
        use_real_market_data=False,
        enable_order_execution=False,
        enable_notifications=False,
        log_level="DEBUG",
        description="Historical data replay for testing"
    ),
    OperatingMode.SIMULATED: ModeConfig(
        mode=OperatingMode.SIMULATED,
        use_real_broker=False,
        use_real_market_data=False,
        enable_order_execution=False,
        enable_notifications=False,
        log_level="DEBUG",
        description="Synthetic data generation for development"
    )
}


class ModeManager:
    """Manages operating mode configuration"""
    
    def __init__(self):
        self._current_mode = self._load_mode_from_env()
    
    def _load_mode_from_env(self) -> OperatingMode:
        """Load operating mode from environment variable"""
        mode_str = os.getenv('OPERATING_MODE', 'paper').lower()
        try:
            return OperatingMode(mode_str)
        except ValueError:
            print(f"Invalid OPERATING_MODE: {mode_str}, defaulting to PAPER")
            return OperatingMode.PAPER
    
    @property
    def current_mode(self) -> OperatingMode:
        """Get current operating mode"""
        return self._current_mode
    
    @property
    def config(self) -> ModeConfig:
        """Get configuration for current mode"""
        return MODE_CONFIGS[self._current_mode]
    
    def set_mode(self, mode: OperatingMode) -> None:
        """Set operating mode"""
        self._current_mode = mode
        os.environ['OPERATING_MODE'] = mode.value
    
    def is_live(self) -> bool:
        """Check if in live trading mode"""
        return self._current_mode == OperatingMode.LIVE
    
    def is_paper(self) -> bool:
        """Check if in paper trading mode"""
        return self._current_mode == OperatingMode.PAPER
    
    def is_replay(self) -> bool:
        """Check if in replay mode"""
        return self._current_mode == OperatingMode.REPLAY
    
    def is_simulated(self) -> bool:
        """Check if in simulated mode"""
        return self._current_mode == OperatingMode.SIMULATED
    
    def should_use_real_broker(self) -> bool:
        """Check if should use real broker connections"""
        return self.config.use_real_broker
    
    def should_use_real_market_data(self) -> bool:
        """Check if should use real market data"""
        return self.config.use_real_market_data
    
    def can_execute_orders(self) -> bool:
        """Check if order execution is enabled"""
        return self.config.enable_order_execution
    
    def should_send_notifications(self) -> bool:
        """Check if notifications are enabled"""
        return self.config.enable_notifications


# Global mode manager instance
mode_manager = ModeManager()
