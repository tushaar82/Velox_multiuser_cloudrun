"""
Strategy State Management

Manages strategy state persistence in Redis for fault tolerance and recovery.
"""

import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime
from redis import Redis

from strategy_workers.strategy_interface import StrategyState, StrategyStatus, StrategyConfig

logger = logging.getLogger(__name__)


class StrategyStateManager:
    """Manages strategy state in Redis"""
    
    def __init__(self, redis_client: Redis):
        """
        Initialize state manager.
        
        Args:
            redis_client: Redis connection
        """
        self.redis = redis_client
        self.state_prefix = "strategy_state:"
        self.active_strategies_key = "active_strategies"
    
    def save_state(self, state: StrategyState) -> None:
        """
        Save strategy state to Redis.
        
        Args:
            state: Strategy state to save
        """
        try:
            key = f"{self.state_prefix}{state.strategy_id}"
            
            # Convert state to dict for JSON serialization
            state_dict = {
                "strategy_id": state.strategy_id,
                "account_id": state.account_id,
                "status": state.status.value,
                "config": self._serialize_config(state.config),
                "started_at": state.started_at.isoformat(),
                "last_update": state.last_update.isoformat(),
                "error_message": state.error_message,
                "custom_state": state.custom_state
            }
            
            # Save to Redis with 24-hour expiration
            self.redis.setex(
                key,
                86400,  # 24 hours
                json.dumps(state_dict)
            )
            
            # Add to active strategies set if running
            if state.status == StrategyStatus.RUNNING:
                self.redis.sadd(self.active_strategies_key, state.strategy_id)
            else:
                self.redis.srem(self.active_strategies_key, state.strategy_id)
            
            logger.debug(f"Saved state for strategy {state.strategy_id}")
            
        except Exception as e:
            logger.error(f"Failed to save strategy state: {e}")
            raise
    
    def load_state(self, strategy_id: str) -> Optional[StrategyState]:
        """
        Load strategy state from Redis.
        
        Args:
            strategy_id: Strategy ID to load
            
        Returns:
            StrategyState if found, None otherwise
        """
        try:
            key = f"{self.state_prefix}{strategy_id}"
            data = self.redis.get(key)
            
            if not data:
                logger.debug(f"No state found for strategy {strategy_id}")
                return None
            
            state_dict = json.loads(data)
            
            # Reconstruct StrategyState object
            state = StrategyState(
                strategy_id=state_dict["strategy_id"],
                account_id=state_dict["account_id"],
                status=StrategyStatus(state_dict["status"]),
                config=self._deserialize_config(state_dict["config"]),
                started_at=datetime.fromisoformat(state_dict["started_at"]),
                last_update=datetime.fromisoformat(state_dict["last_update"]),
                error_message=state_dict.get("error_message"),
                custom_state=state_dict.get("custom_state", {})
            )
            
            logger.debug(f"Loaded state for strategy {strategy_id}")
            return state
            
        except Exception as e:
            logger.error(f"Failed to load strategy state: {e}")
            return None
    
    def delete_state(self, strategy_id: str) -> None:
        """
        Delete strategy state from Redis.
        
        Args:
            strategy_id: Strategy ID to delete
        """
        try:
            key = f"{self.state_prefix}{strategy_id}"
            self.redis.delete(key)
            self.redis.srem(self.active_strategies_key, strategy_id)
            logger.debug(f"Deleted state for strategy {strategy_id}")
            
        except Exception as e:
            logger.error(f"Failed to delete strategy state: {e}")
    
    def get_active_strategies(self) -> list[str]:
        """
        Get list of all active strategy IDs.
        
        Returns:
            List of strategy IDs
        """
        try:
            strategy_ids = self.redis.smembers(self.active_strategies_key)
            return [sid.decode('utf-8') if isinstance(sid, bytes) else sid 
                    for sid in strategy_ids]
        except Exception as e:
            logger.error(f"Failed to get active strategies: {e}")
            return []
    
    def update_status(self, strategy_id: str, status: StrategyStatus, 
                     error_message: Optional[str] = None) -> None:
        """
        Update strategy status.
        
        Args:
            strategy_id: Strategy ID
            status: New status
            error_message: Optional error message if status is ERROR
        """
        state = self.load_state(strategy_id)
        if state:
            state.status = status
            state.last_update = datetime.utcnow()
            state.error_message = error_message
            self.save_state(state)
    
    def update_custom_state(self, strategy_id: str, custom_state: Dict[str, Any]) -> None:
        """
        Update strategy custom state.
        
        Args:
            strategy_id: Strategy ID
            custom_state: Custom state dictionary
        """
        state = self.load_state(strategy_id)
        if state:
            state.custom_state = custom_state
            state.last_update = datetime.utcnow()
            self.save_state(state)
    
    def _serialize_config(self, config: StrategyConfig) -> Dict[str, Any]:
        """Serialize StrategyConfig to dict"""
        return {
            "strategy_id": config.strategy_id,
            "account_id": config.account_id,
            "trading_mode": config.trading_mode,
            "symbols": config.symbols,
            "timeframes": config.timeframes,
            "parameters": config.parameters,
            "risk_management": {
                "max_position_size": config.risk_management.max_position_size,
                "max_loss_per_trade": config.risk_management.max_loss_per_trade,
                "stop_loss_percentage": config.risk_management.stop_loss_percentage,
                "take_profit_percentage": config.risk_management.take_profit_percentage,
                "trailing_stop_percentage": config.risk_management.trailing_stop_percentage
            } if config.risk_management else None
        }
    
    def _deserialize_config(self, config_dict: Dict[str, Any]) -> StrategyConfig:
        """Deserialize dict to StrategyConfig"""
        from strategy_workers.strategy_interface import RiskConfig
        
        risk_config = None
        if config_dict.get("risk_management"):
            rm = config_dict["risk_management"]
            risk_config = RiskConfig(
                max_position_size=rm.get("max_position_size", 100),
                max_loss_per_trade=rm.get("max_loss_per_trade", 1000.0),
                stop_loss_percentage=rm.get("stop_loss_percentage"),
                take_profit_percentage=rm.get("take_profit_percentage"),
                trailing_stop_percentage=rm.get("trailing_stop_percentage")
            )
        
        return StrategyConfig(
            strategy_id=config_dict["strategy_id"],
            account_id=config_dict["account_id"],
            trading_mode=config_dict["trading_mode"],
            symbols=config_dict["symbols"],
            timeframes=config_dict["timeframes"],
            parameters=config_dict["parameters"],
            risk_management=risk_config
        )
