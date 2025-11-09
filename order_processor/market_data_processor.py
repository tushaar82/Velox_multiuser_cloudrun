"""
Market Data Processor for Order Processor Service

Listens to market data updates and triggers position updates and trailing stop checks.
"""
import logging
import json
from typing import Dict, Any
from redis import Redis
from sqlalchemy.orm import Session
from shared.models.order import TradingMode
from shared.utils.logging_config import get_logger
from order_processor.position_manager import PositionManager
from order_processor.trailing_stop_order_handler import TrailingStopOrderHandler

logger = get_logger(__name__)


class MarketDataProcessor:
    """
    Processes market data updates for position management.
    
    Responsibilities:
    1. Listen to market data updates via Redis pub/sub
    2. Update position prices and P&L
    3. Trigger trailing stop checks
    4. Broadcast position updates
    """
    
    def __init__(
        self,
        db_session: Session,
        redis_client: Redis,
        position_manager: PositionManager,
        trailing_stop_handler: TrailingStopOrderHandler
    ):
        """
        Initialize market data processor.
        
        Args:
            db_session: Database session
            redis_client: Redis client for pub/sub
            position_manager: Position manager instance
            trailing_stop_handler: Trailing stop order handler
        """
        self.db = db_session
        self.redis = redis_client
        self.position_manager = position_manager
        self.trailing_stop_handler = trailing_stop_handler
        self.pubsub = None
        self.running = False
        
        logger.info("Market data processor initialized")
    
    def start(self) -> None:
        """Start listening to market data updates."""
        try:
            # Subscribe to market data channel
            self.pubsub = self.redis.pubsub()
            self.pubsub.subscribe('market_data:tick_update')
            
            self.running = True
            logger.info("Market data processor started, listening for tick updates")
            
            # Process messages
            for message in self.pubsub.listen():
                if not self.running:
                    break
                
                if message['type'] == 'message':
                    self._process_tick_update(message['data'])
                    
        except Exception as e:
            logger.error(f"Error in market data processor: {e}", exc_info=True)
        finally:
            self.stop()
    
    def stop(self) -> None:
        """Stop listening to market data updates."""
        self.running = False
        
        if self.pubsub:
            self.pubsub.unsubscribe()
            self.pubsub.close()
        
        logger.info("Market data processor stopped")
    
    def _process_tick_update(self, data: bytes) -> None:
        """
        Process tick update message.
        
        Args:
            data: JSON-encoded tick data
        """
        try:
            # Parse tick data
            tick_data = json.loads(data)
            symbol = tick_data.get('symbol')
            price = tick_data.get('price')
            
            if not symbol or price is None:
                logger.warning(f"Invalid tick data: {tick_data}")
                return
            
            # Update positions for both paper and live trading
            self._update_positions_for_symbol(symbol, price, TradingMode.PAPER)
            self._update_positions_for_symbol(symbol, price, TradingMode.LIVE)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse tick data: {e}")
        except Exception as e:
            logger.error(f"Error processing tick update: {e}", exc_info=True)
    
    def _update_positions_for_symbol(
        self,
        symbol: str,
        price: float,
        trading_mode: TradingMode
    ) -> None:
        """
        Update all positions for a symbol and check trailing stops.
        
        Args:
            symbol: Symbol to update
            price: Current price
            trading_mode: Trading mode
        """
        try:
            # Update position prices and P&L
            updated_positions = self.position_manager.update_all_positions_price(
                symbol,
                price,
                trading_mode
            )
            
            if updated_positions:
                logger.debug(
                    f"Updated {len(updated_positions)} positions for {symbol} "
                    f"@ {price} (mode: {trading_mode.value})"
                )
                
                # Broadcast position updates via WebSocket
                self._broadcast_position_updates(updated_positions)
            
            # Check trailing stops for this symbol
            triggered_count = self.trailing_stop_handler.process_price_update(
                symbol,
                price,
                trading_mode
            )
            
            if triggered_count > 0:
                logger.info(
                    f"Triggered {triggered_count} trailing stops for {symbol} "
                    f"@ {price} (mode: {trading_mode.value})"
                )
            
        except Exception as e:
            logger.error(
                f"Error updating positions for {symbol} @ {price}: {e}",
                exc_info=True
            )
    
    def _broadcast_position_updates(self, positions: list) -> None:
        """
        Broadcast position updates via Redis pub/sub for WebSocket distribution.
        
        Args:
            positions: List of updated position data
        """
        try:
            for position in positions:
                # Publish to position update channel
                position_dict = {
                    'id': position.id,
                    'account_id': position.account_id,
                    'symbol': position.symbol,
                    'side': position.side.value,
                    'quantity': position.quantity,
                    'entry_price': position.entry_price,
                    'current_price': position.current_price,
                    'unrealized_pnl': position.unrealized_pnl,
                    'realized_pnl': position.realized_pnl,
                    'trading_mode': position.trading_mode.value,
                    'trailing_stop_loss': {
                        'enabled': position.trailing_stop_loss.enabled,
                        'percentage': position.trailing_stop_loss.percentage,
                        'current_stop_price': position.trailing_stop_loss.current_stop_price,
                        'highest_price': position.trailing_stop_loss.highest_price,
                        'lowest_price': position.trailing_stop_loss.lowest_price
                    } if position.trailing_stop_loss else None
                }
                
                self.redis.publish(
                    f'position_update:{position.account_id}:{position.trading_mode.value}',
                    json.dumps(position_dict)
                )
                
        except Exception as e:
            logger.error(f"Error broadcasting position updates: {e}")
    
    def process_single_tick(
        self,
        symbol: str,
        price: float,
        trading_mode: TradingMode
    ) -> Dict[str, Any]:
        """
        Process a single tick update synchronously (for testing or manual triggers).
        
        Args:
            symbol: Symbol
            price: Current price
            trading_mode: Trading mode
            
        Returns:
            Dictionary with update results
        """
        updated_positions = self.position_manager.update_all_positions_price(
            symbol,
            price,
            trading_mode
        )
        
        triggered_count = self.trailing_stop_handler.process_price_update(
            symbol,
            price,
            trading_mode
        )
        
        return {
            'symbol': symbol,
            'price': price,
            'trading_mode': trading_mode.value,
            'positions_updated': len(updated_positions),
            'trailing_stops_triggered': triggered_count
        }
