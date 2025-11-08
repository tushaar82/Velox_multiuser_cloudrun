"""Trailing stop-loss manager for automatic stop price updates."""

from typing import Optional, List, Callable
from sqlalchemy.orm import Session
import uuid
from shared.models.position import Position, PositionData, PositionSide, TrailingStopConfig
from shared.models.order import TradingMode
from shared.utils.logging_config import get_logger

logger = get_logger(__name__)


class TrailingStopManager:
    """Manages trailing stop-loss for positions."""
    
    def __init__(self, db_session: Session):
        """
        Initialize trailing stop manager.
        
        Args:
            db_session: Database session
        """
        self.db = db_session
        self.stop_triggered_callbacks: List[Callable] = []
        logger.info("Trailing stop manager initialized")
    
    def configure_trailing_stop(
        self,
        position_id: str,
        percentage: float,
        current_price: float
    ) -> PositionData:
        """
        Configure trailing stop-loss for a position.
        
        Args:
            position_id: Position ID
            percentage: Trailing stop percentage (e.g., 0.02 for 2%)
            current_price: Current market price
            
        Returns:
            Updated position data
        """
        position = self.db.query(Position).filter(Position.id == uuid.UUID(position_id)).first()
        if not position:
            raise ValueError(f"Position {position_id} not found")
        
        if position.closed_at:
            raise ValueError(f"Position {position_id} is already closed")
        
        if percentage <= 0 or percentage >= 1:
            raise ValueError("Trailing stop percentage must be between 0 and 1")
        
        # Calculate initial stop price
        if position.side == PositionSide.LONG:
            stop_price = current_price * (1 - percentage)
            highest_price = max(current_price, float(position.entry_price))
            lowest_price = 0
        else:  # SHORT
            stop_price = current_price * (1 + percentage)
            highest_price = 0
            lowest_price = min(current_price, float(position.entry_price))
        
        # Create trailing stop config
        trailing_config = {
            'enabled': True,
            'percentage': percentage,
            'current_stop_price': round(stop_price, 2),
            'highest_price': round(highest_price, 2),
            'lowest_price': round(lowest_price, 2)
        }
        
        position.trailing_stop_config = trailing_config
        self.db.commit()
        self.db.refresh(position)
        
        logger.info(
            f"Configured trailing stop for position {position_id}: "
            f"{percentage*100:.1f}% @ {stop_price:.2f}"
        )
        
        return PositionData.from_orm(position)
    
    def update_trailing_stop(
        self,
        position_id: str,
        current_price: float
    ) -> tuple[PositionData, bool]:
        """
        Update trailing stop price based on current market price.
        
        Args:
            position_id: Position ID
            current_price: Current market price
            
        Returns:
            Tuple of (updated position data, stop triggered flag)
        """
        position = self.db.query(Position).filter(Position.id == uuid.UUID(position_id)).first()
        if not position:
            raise ValueError(f"Position {position_id} not found")
        
        if not position.trailing_stop_config or not position.trailing_stop_config.get('enabled'):
            return PositionData.from_orm(position), False
        
        if position.closed_at:
            return PositionData.from_orm(position), False
        
        config = position.trailing_stop_config
        percentage = config['percentage']
        current_stop = config['current_stop_price']
        
        stop_triggered = False
        
        if position.side == PositionSide.LONG:
            # Update highest price
            highest_price = max(current_price, config['highest_price'])
            config['highest_price'] = round(highest_price, 2)
            
            # Calculate new stop price
            new_stop = highest_price * (1 - percentage)
            
            # Only update if new stop is higher (trailing up)
            if new_stop > current_stop:
                config['current_stop_price'] = round(new_stop, 2)
                logger.debug(
                    f"Updated trailing stop for LONG position {position_id}: "
                    f"{current_stop:.2f} -> {new_stop:.2f}"
                )
            
            # Check if stop is triggered
            if current_price <= config['current_stop_price']:
                stop_triggered = True
                logger.info(
                    f"Trailing stop triggered for LONG position {position_id}: "
                    f"price {current_price:.2f} <= stop {config['current_stop_price']:.2f}"
                )
        
        else:  # SHORT
            # Update lowest price
            lowest_price = min(current_price, config['lowest_price'])
            config['lowest_price'] = round(lowest_price, 2)
            
            # Calculate new stop price
            new_stop = lowest_price * (1 + percentage)
            
            # Only update if new stop is lower (trailing down)
            if new_stop < current_stop:
                config['current_stop_price'] = round(new_stop, 2)
                logger.debug(
                    f"Updated trailing stop for SHORT position {position_id}: "
                    f"{current_stop:.2f} -> {new_stop:.2f}"
                )
            
            # Check if stop is triggered
            if current_price >= config['current_stop_price']:
                stop_triggered = True
                logger.info(
                    f"Trailing stop triggered for SHORT position {position_id}: "
                    f"price {current_price:.2f} >= stop {config['current_stop_price']:.2f}"
                )
        
        position.trailing_stop_config = config
        self.db.commit()
        self.db.refresh(position)
        
        position_data = PositionData.from_orm(position)
        
        # Trigger callbacks if stop triggered
        if stop_triggered:
            self._trigger_stop_callbacks(position_data)
        
        return position_data, stop_triggered
    
    def disable_trailing_stop(self, position_id: str) -> PositionData:
        """
        Disable trailing stop-loss for a position.
        
        Args:
            position_id: Position ID
            
        Returns:
            Updated position data
        """
        position = self.db.query(Position).filter(Position.id == uuid.UUID(position_id)).first()
        if not position:
            raise ValueError(f"Position {position_id} not found")
        
        if position.trailing_stop_config:
            position.trailing_stop_config['enabled'] = False
            self.db.commit()
            self.db.refresh(position)
            
            logger.info(f"Disabled trailing stop for position {position_id}")
        
        return PositionData.from_orm(position)
    
    def check_all_trailing_stops(
        self,
        symbol: str,
        current_price: float,
        trading_mode: TradingMode
    ) -> List[tuple[PositionData, bool]]:
        """
        Check and update trailing stops for all positions of a symbol.
        
        Args:
            symbol: Symbol to check
            current_price: Current market price
            trading_mode: Trading mode filter
            
        Returns:
            List of (position data, stop triggered) tuples
        """
        positions = self.db.query(Position).filter(
            Position.symbol == symbol,
            Position.trading_mode == trading_mode,
            Position.closed_at.is_(None),
            Position.trailing_stop_config.isnot(None)
        ).all()
        
        results = []
        for position in positions:
            if position.trailing_stop_config and position.trailing_stop_config.get('enabled'):
                try:
                    position_data, triggered = self.update_trailing_stop(
                        str(position.id),
                        current_price
                    )
                    results.append((position_data, triggered))
                except Exception as e:
                    logger.error(f"Error updating trailing stop for position {position.id}: {e}")
        
        return results
    
    def get_trailing_stop_info(self, position_id: str) -> Optional[TrailingStopConfig]:
        """
        Get trailing stop configuration for a position.
        
        Args:
            position_id: Position ID
            
        Returns:
            TrailingStopConfig or None if not configured
        """
        position = self.db.query(Position).filter(Position.id == uuid.UUID(position_id)).first()
        if not position or not position.trailing_stop_config:
            return None
        
        config = position.trailing_stop_config
        return TrailingStopConfig(
            enabled=config.get('enabled', False),
            percentage=config.get('percentage', 0),
            current_stop_price=config.get('current_stop_price', 0),
            highest_price=config.get('highest_price', 0),
            lowest_price=config.get('lowest_price', 0)
        )
    
    def register_stop_triggered_callback(self, callback: Callable[[PositionData], None]) -> None:
        """
        Register callback to be called when trailing stop is triggered.
        
        Args:
            callback: Function to call with position data when stop triggered
        """
        self.stop_triggered_callbacks.append(callback)
        logger.info("Registered trailing stop triggered callback")
    
    def _trigger_stop_callbacks(self, position: PositionData) -> None:
        """Trigger all registered callbacks for stop triggered event."""
        for callback in self.stop_triggered_callbacks:
            try:
                callback(position)
            except Exception as e:
                logger.error(f"Error in trailing stop callback: {e}")
    
    def get_positions_with_trailing_stops(
        self,
        account_id: str,
        trading_mode: TradingMode
    ) -> List[PositionData]:
        """
        Get all positions with active trailing stops for an account.
        
        Args:
            account_id: Account ID
            trading_mode: Trading mode filter
            
        Returns:
            List of position data with trailing stops
        """
        positions = self.db.query(Position).filter(
            Position.account_id == uuid.UUID(account_id),
            Position.trading_mode == trading_mode,
            Position.closed_at.is_(None),
            Position.trailing_stop_config.isnot(None)
        ).all()
        
        result = []
        for position in positions:
            if position.trailing_stop_config and position.trailing_stop_config.get('enabled'):
                result.append(PositionData.from_orm(position))
        
        return result
