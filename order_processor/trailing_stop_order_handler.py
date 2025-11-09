"""
Trailing Stop Order Handler

Integrates trailing stop manager with order router to automatically generate
exit orders when trailing stops are triggered.
"""
import logging
from typing import Optional
from sqlalchemy.orm import Session
from shared.models.position import PositionData, PositionSide
from shared.models.order import OrderSide, TradingMode
from shared.utils.logging_config import get_logger
from order_processor.trailing_stop_manager import TrailingStopManager
from order_processor.order_router import OrderRouter

logger = get_logger(__name__)


class TrailingStopOrderHandler:
    """
    Handles automatic order generation when trailing stops are triggered.
    
    This service:
    1. Monitors trailing stop triggers from TrailingStopManager
    2. Generates exit orders automatically
    3. Notifies users of trailing stop executions
    """
    
    def __init__(
        self,
        db_session: Session,
        trailing_stop_manager: TrailingStopManager,
        order_router: OrderRouter
    ):
        """
        Initialize trailing stop order handler.
        
        Args:
            db_session: Database session
            trailing_stop_manager: Trailing stop manager instance
            order_router: Order router for submitting exit orders
        """
        self.db = db_session
        self.trailing_stop_manager = trailing_stop_manager
        self.order_router = order_router
        
        # Register callback with trailing stop manager
        self.trailing_stop_manager.register_stop_triggered_callback(
            self._on_trailing_stop_triggered
        )
        
        logger.info("Trailing stop order handler initialized")
    
    def process_price_update(
        self,
        symbol: str,
        current_price: float,
        trading_mode: TradingMode
    ) -> int:
        """
        Process price update and check all trailing stops for the symbol.
        
        This should be called whenever market price updates are received.
        
        Args:
            symbol: Symbol that was updated
            current_price: Current market price
            trading_mode: Trading mode (paper/live)
            
        Returns:
            Number of trailing stops triggered
        """
        try:
            # Check all trailing stops for this symbol
            results = self.trailing_stop_manager.check_all_trailing_stops(
                symbol,
                current_price,
                trading_mode
            )
            
            triggered_count = sum(1 for _, triggered in results if triggered)
            
            if triggered_count > 0:
                logger.info(
                    f"Processed {len(results)} trailing stops for {symbol}, "
                    f"{triggered_count} triggered"
                )
            
            return triggered_count
            
        except Exception as e:
            logger.error(f"Error processing price update for {symbol}: {e}")
            return 0
    
    def _on_trailing_stop_triggered(self, position: PositionData) -> None:
        """
        Callback when trailing stop is triggered.
        
        Automatically generates exit order for the position.
        
        Args:
            position: Position with triggered trailing stop
        """
        try:
            logger.info(
                f"Trailing stop triggered for position {position.id}: "
                f"{position.symbol} {position.side.value} {position.quantity}"
            )
            
            # Determine exit order side (opposite of position side)
            exit_side = OrderSide.SELL if position.side == PositionSide.LONG else OrderSide.BUY
            
            # Get current stop price from trailing config
            stop_price = None
            if position.trailing_stop_loss:
                stop_price = position.trailing_stop_loss.current_stop_price
            
            # Submit market exit order
            exit_order = self.order_router.submit_order(
                account_id=position.account_id,
                symbol=position.symbol,
                side=exit_side,
                quantity=position.quantity,
                order_type='market',
                trading_mode=position.trading_mode,
                strategy_id=position.strategy_id,
                current_market_price=stop_price  # Use stop price for paper trading
            )
            
            logger.info(
                f"Generated exit order {exit_order.id} for trailing stop trigger: "
                f"{position.symbol} {exit_side.value} {position.quantity} @ market"
            )
            
            # Send notification (this would integrate with notification service)
            self._send_trailing_stop_notification(position, exit_order.id)
            
        except Exception as e:
            logger.error(
                f"Error generating exit order for trailing stop trigger "
                f"(position {position.id}): {e}",
                exc_info=True
            )
    
    def _send_trailing_stop_notification(
        self,
        position: PositionData,
        exit_order_id: str
    ) -> None:
        """
        Send notification about trailing stop trigger.
        
        Args:
            position: Position that triggered
            exit_order_id: ID of generated exit order
        """
        try:
            # TODO: Integrate with notification service
            # For now, just log
            logger.info(
                f"Notification: Trailing stop triggered for {position.symbol} "
                f"position {position.id}, exit order {exit_order_id} submitted"
            )
            
            # In production, this would call:
            # notification_service.send_notification(
            #     user_id=position.account_id,
            #     type='trailing_stop_triggered',
            #     title='Trailing Stop Triggered',
            #     message=f'Trailing stop triggered for {position.symbol} position. '
            #             f'Exit order submitted.',
            #     severity='info',
            #     channels=['in_app', 'email']
            # )
            
        except Exception as e:
            logger.error(f"Error sending trailing stop notification: {e}")
    
    def configure_trailing_stop_with_validation(
        self,
        position_id: str,
        percentage: float,
        current_price: float
    ) -> PositionData:
        """
        Configure trailing stop with validation.
        
        Args:
            position_id: Position ID
            percentage: Trailing stop percentage (0.001 to 0.1 = 0.1% to 10%)
            current_price: Current market price
            
        Returns:
            Updated position data
            
        Raises:
            ValueError: If validation fails
        """
        # Validate percentage range
        if percentage < 0.001 or percentage > 0.1:
            raise ValueError(
                "Trailing stop percentage must be between 0.1% and 10% "
                "(0.001 to 0.1)"
            )
        
        # Configure trailing stop
        return self.trailing_stop_manager.configure_trailing_stop(
            position_id,
            percentage,
            current_price
        )
    
    def disable_trailing_stop(self, position_id: str) -> PositionData:
        """
        Disable trailing stop for a position.
        
        Args:
            position_id: Position ID
            
        Returns:
            Updated position data
        """
        return self.trailing_stop_manager.disable_trailing_stop(position_id)
    
    def get_trailing_stop_info(self, position_id: str):
        """
        Get trailing stop configuration for a position.
        
        Args:
            position_id: Position ID
            
        Returns:
            TrailingStopConfig or None
        """
        return self.trailing_stop_manager.get_trailing_stop_info(position_id)
