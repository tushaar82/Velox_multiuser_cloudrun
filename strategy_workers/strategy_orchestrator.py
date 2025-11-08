"""
Strategy Execution Orchestrator

Manages strategy lifecycle, execution, and error handling.
"""

import logging
import traceback
from typing import Dict, Optional, List
from datetime import datetime
from redis import Redis

from strategy_workers.strategy_interface import (
    IStrategy, StrategyConfig, StrategyState, StrategyStatus,
    Signal, MultiTimeframeData, Candle
)
from strategy_workers.strategy_plugin_manager import StrategyPluginManager
from strategy_workers.strategy_state_manager import StrategyStateManager
from strategy_workers.multi_timeframe_provider import MultiTimeframeDataProvider

logger = logging.getLogger(__name__)


class StrategyOrchestrator:
    """Orchestrates strategy execution and lifecycle management"""
    
    def __init__(self, redis_client: Redis, plugin_manager: StrategyPluginManager,
                 state_manager: StrategyStateManager, data_provider: MultiTimeframeDataProvider):
        """
        Initialize orchestrator.
        
        Args:
            redis_client: Redis connection
            plugin_manager: Strategy plugin manager
            state_manager: Strategy state manager
            data_provider: Multi-timeframe data provider
        """
        self.redis = redis_client
        self.plugin_manager = plugin_manager
        self.state_manager = state_manager
        self.data_provider = data_provider
        self.active_strategies: Dict[str, IStrategy] = {}
        self.strategy_configs: Dict[str, StrategyConfig] = {}
    
    def load_strategy(self, config: StrategyConfig, strategy_name: str) -> bool:
        """
        Load and initialize a strategy.
        
        Args:
            config: Strategy configuration
            strategy_name: Name of the strategy to load
            
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            # Check if strategy already loaded
            if config.strategy_id in self.active_strategies:
                logger.warning(f"Strategy {config.strategy_id} already loaded")
                return False
            
            # Get strategy class from plugin manager
            strategy_class = self.plugin_manager.get_strategy(strategy_name)
            if not strategy_class:
                logger.error(f"Strategy '{strategy_name}' not found")
                return False
            
            # Validate parameters
            is_valid, error_msg = self.plugin_manager.validate_parameters(
                strategy_name, config.parameters
            )
            if not is_valid:
                logger.error(f"Invalid parameters: {error_msg}")
                return False
            
            # Check concurrent strategy limit
            if not self._check_concurrent_limit(config.account_id, config.trading_mode):
                logger.error(f"Concurrent strategy limit reached for account {config.account_id}")
                return False
            
            # Instantiate strategy
            strategy_instance = strategy_class()
            
            # Initialize strategy
            strategy_instance.initialize(config)
            
            # Store strategy instance and config
            self.active_strategies[config.strategy_id] = strategy_instance
            self.strategy_configs[config.strategy_id] = config
            
            # Create and save initial state
            state = StrategyState(
                strategy_id=config.strategy_id,
                account_id=config.account_id,
                status=StrategyStatus.RUNNING,
                config=config,
                started_at=datetime.utcnow(),
                last_update=datetime.utcnow()
            )
            self.state_manager.save_state(state)
            
            logger.info(f"Loaded strategy {config.strategy_id} ({strategy_name})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to load strategy: {e}")
            logger.error(traceback.format_exc())
            return False
    
    def execute_on_tick(self, symbol: str, strategy_id: str) -> Optional[Signal]:
        """
        Execute strategy on tick update.
        
        Args:
            symbol: Symbol that was updated
            strategy_id: Strategy ID to execute
            
        Returns:
            Signal if generated, None otherwise
        """
        try:
            strategy = self.active_strategies.get(strategy_id)
            config = self.strategy_configs.get(strategy_id)
            
            if not strategy or not config:
                logger.warning(f"Strategy {strategy_id} not found")
                return None
            
            # Check if strategy is running
            state = self.state_manager.load_state(strategy_id)
            if not state or state.status != StrategyStatus.RUNNING:
                return None
            
            # Check if symbol is in strategy's symbols
            if symbol not in config.symbols:
                return None
            
            # Get multi-timeframe data
            data = self.data_provider.get_data(
                symbol=symbol,
                timeframes=config.timeframes,
                indicator_configs=self._get_indicator_configs(config)
            )
            
            # Verify data consistency
            if not self.data_provider.ensure_data_consistency(data):
                logger.warning(f"Inconsistent data for {symbol}, skipping tick")
                return None
            
            # Execute strategy
            signal = strategy.on_tick(data)
            
            # Validate signal if generated
            if signal:
                if self._validate_signal(signal, config):
                    logger.info(f"Strategy {strategy_id} generated signal: {signal.type} {signal.direction} {signal.symbol}")
                    return signal
                else:
                    logger.warning(f"Invalid signal from strategy {strategy_id}")
                    return None
            
            return None
            
        except Exception as e:
            logger.error(f"Error executing strategy {strategy_id} on tick: {e}")
            logger.error(traceback.format_exc())
            self._handle_strategy_error(strategy_id, str(e))
            return None
    
    def execute_on_candle_complete(self, symbol: str, timeframe: str, 
                                   candle: Candle, strategy_id: str) -> Optional[Signal]:
        """
        Execute strategy on candle completion.
        
        Args:
            symbol: Symbol of completed candle
            timeframe: Timeframe of completed candle
            candle: Completed candle
            strategy_id: Strategy ID to execute
            
        Returns:
            Signal if generated, None otherwise
        """
        try:
            strategy = self.active_strategies.get(strategy_id)
            config = self.strategy_configs.get(strategy_id)
            
            if not strategy or not config:
                logger.warning(f"Strategy {strategy_id} not found")
                return None
            
            # Check if strategy is running
            state = self.state_manager.load_state(strategy_id)
            if not state or state.status != StrategyStatus.RUNNING:
                return None
            
            # Check if symbol and timeframe are relevant
            if symbol not in config.symbols or timeframe not in config.timeframes:
                return None
            
            # Get multi-timeframe data
            data = self.data_provider.get_data(
                symbol=symbol,
                timeframes=config.timeframes,
                indicator_configs=self._get_indicator_configs(config)
            )
            
            # Execute strategy
            signal = strategy.on_candle_complete(timeframe, candle, data)
            
            # Validate signal if generated
            if signal:
                if self._validate_signal(signal, config):
                    logger.info(f"Strategy {strategy_id} generated signal on candle complete: {signal.type} {signal.direction} {signal.symbol}")
                    return signal
                else:
                    logger.warning(f"Invalid signal from strategy {strategy_id}")
                    return None
            
            return None
            
        except Exception as e:
            logger.error(f"Error executing strategy {strategy_id} on candle complete: {e}")
            logger.error(traceback.format_exc())
            self._handle_strategy_error(strategy_id, str(e))
            return None
    
    def pause_strategy(self, strategy_id: str) -> bool:
        """
        Pause a running strategy.
        
        Args:
            strategy_id: Strategy ID to pause
            
        Returns:
            True if paused successfully, False otherwise
        """
        try:
            if strategy_id not in self.active_strategies:
                logger.warning(f"Strategy {strategy_id} not found")
                return False
            
            # Update state to paused
            self.state_manager.update_status(strategy_id, StrategyStatus.PAUSED)
            logger.info(f"Paused strategy {strategy_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to pause strategy {strategy_id}: {e}")
            return False
    
    def resume_strategy(self, strategy_id: str) -> bool:
        """
        Resume a paused strategy.
        
        Args:
            strategy_id: Strategy ID to resume
            
        Returns:
            True if resumed successfully, False otherwise
        """
        try:
            if strategy_id not in self.active_strategies:
                logger.warning(f"Strategy {strategy_id} not found")
                return False
            
            state = self.state_manager.load_state(strategy_id)
            if not state or state.status != StrategyStatus.PAUSED:
                logger.warning(f"Strategy {strategy_id} is not paused")
                return False
            
            # Update state to running
            self.state_manager.update_status(strategy_id, StrategyStatus.RUNNING)
            logger.info(f"Resumed strategy {strategy_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to resume strategy {strategy_id}: {e}")
            return False
    
    def stop_strategy(self, strategy_id: str) -> bool:
        """
        Stop and cleanup a strategy.
        
        Args:
            strategy_id: Strategy ID to stop
            
        Returns:
            True if stopped successfully, False otherwise
        """
        try:
            strategy = self.active_strategies.get(strategy_id)
            
            if not strategy:
                logger.warning(f"Strategy {strategy_id} not found")
                return False
            
            # Call cleanup
            strategy.cleanup()
            
            # Remove from active strategies
            del self.active_strategies[strategy_id]
            del self.strategy_configs[strategy_id]
            
            # Update state to stopped
            self.state_manager.update_status(strategy_id, StrategyStatus.STOPPED)
            
            logger.info(f"Stopped strategy {strategy_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop strategy {strategy_id}: {e}")
            return False
    
    def pause_all_strategies(self, account_id: str, reason: str) -> int:
        """
        Pause all strategies for an account.
        
        Args:
            account_id: Account ID
            reason: Reason for pausing (e.g., "loss limit breached")
            
        Returns:
            Number of strategies paused
        """
        count = 0
        
        for strategy_id, config in self.strategy_configs.items():
            if config.account_id == account_id:
                if self.pause_strategy(strategy_id):
                    count += 1
        
        logger.info(f"Paused {count} strategies for account {account_id}. Reason: {reason}")
        return count
    
    def _validate_signal(self, signal: Signal, config: StrategyConfig) -> bool:
        """
        Validate a trading signal.
        
        Args:
            signal: Signal to validate
            config: Strategy configuration
            
        Returns:
            True if valid, False otherwise
        """
        # Check required fields
        if not signal.symbol or not signal.type or not signal.direction:
            return False
        
        # Check signal type
        if signal.type not in ['entry', 'exit']:
            return False
        
        # Check direction
        if signal.direction not in ['long', 'short']:
            return False
        
        # Check order type
        if signal.order_type not in ['market', 'limit']:
            return False
        
        # Check quantity
        if signal.quantity <= 0:
            return False
        
        # Check symbol is in strategy's symbols
        if signal.symbol not in config.symbols:
            return False
        
        # Check limit price for limit orders
        if signal.order_type == 'limit' and signal.price is None:
            return False
        
        return True
    
    def _handle_strategy_error(self, strategy_id: str, error_message: str) -> None:
        """
        Handle strategy execution error.
        
        Args:
            strategy_id: Strategy ID that errored
            error_message: Error message
        """
        try:
            # Update state to error
            self.state_manager.update_status(
                strategy_id, 
                StrategyStatus.ERROR,
                error_message=error_message
            )
            
            # Pause the strategy
            self.pause_strategy(strategy_id)
            
            logger.error(f"Strategy {strategy_id} encountered error and was paused: {error_message}")
            
            # TODO: Send notification to user
            
        except Exception as e:
            logger.error(f"Failed to handle strategy error: {e}")
    
    def _check_concurrent_limit(self, account_id: str, trading_mode: str) -> bool:
        """
        Check if account can activate another strategy.
        
        Args:
            account_id: Account ID
            trading_mode: Trading mode ('paper' or 'live')
            
        Returns:
            True if under limit, False otherwise
        """
        # Get active strategy count for account and trading mode
        active_count = sum(
            1 for config in self.strategy_configs.values()
            if config.account_id == account_id and config.trading_mode == trading_mode
        )
        
        # Get limit from Redis or database
        # For now, use a default limit of 5
        max_limit = 5
        
        return active_count < max_limit
    
    def _get_indicator_configs(self, config: StrategyConfig) -> Optional[Dict[str, List[Dict]]]:
        """
        Extract indicator configurations from strategy parameters.
        
        Args:
            config: Strategy configuration
            
        Returns:
            Dict of {timeframe: [indicator_configs]} or None
        """
        # This would be extracted from strategy config
        # For now, return None - strategies will specify their own indicators
        return None
    
    def get_active_strategy_count(self, account_id: str, trading_mode: str) -> int:
        """
        Get count of active strategies for an account.
        
        Args:
            account_id: Account ID
            trading_mode: Trading mode
            
        Returns:
            Count of active strategies
        """
        return sum(
            1 for config in self.strategy_configs.values()
            if config.account_id == account_id and config.trading_mode == trading_mode
        )
    
    def get_strategy_state(self, strategy_id: str) -> Optional[StrategyState]:
        """
        Get current state of a strategy.
        
        Args:
            strategy_id: Strategy ID
            
        Returns:
            StrategyState if found, None otherwise
        """
        return self.state_manager.load_state(strategy_id)
