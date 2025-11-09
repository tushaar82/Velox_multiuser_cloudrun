"""
Order Processing Service Entry Point

Background service that processes orders and manages positions.
"""
import logging
import time
import signal
import sys
from redis import Redis

from shared.utils.logging_config import setup_logging
from shared.config.settings import get_settings
from shared.database.connection import get_db_session
from shared.services.symbol_mapping_service import SymbolMappingService
from order_processor.order_router import OrderRouter
from order_processor.paper_trading_simulator import PaperTradingSimulator
from order_processor.position_manager import PositionManager
from order_processor.trailing_stop_manager import TrailingStopManager
from order_processor.trailing_stop_order_handler import TrailingStopOrderHandler
from order_processor.market_data_processor import MarketDataProcessor

# Setup logging
setup_logging('order_processor')
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Global flag for graceful shutdown
running = True
market_data_processor = None


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully"""
    global running, market_data_processor
    logger.info(f"Received signal {sig}, initiating graceful shutdown...")
    running = False
    if market_data_processor:
        market_data_processor.stop()


def main():
    """Main execution loop"""
    global running, market_data_processor
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Initialize Redis
    redis_client = Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        db=0,
        decode_responses=True
    )
    
    # Initialize database session
    db_session = get_db_session()
    
    # Initialize components
    symbol_mapping_service = SymbolMappingService(db_session, redis_client)
    paper_simulator = PaperTradingSimulator(db_session, redis_client)
    position_manager = PositionManager(db_session)
    trailing_stop_manager = TrailingStopManager(db_session)
    
    # Initialize order router
    order_router = OrderRouter(
        db_session=db_session,
        symbol_mapping_service=symbol_mapping_service,
        broker_connectors={},  # Broker connectors would be initialized here
        paper_trading_simulator=paper_simulator
    )
    
    # Initialize trailing stop order handler
    trailing_stop_handler = TrailingStopOrderHandler(
        db_session=db_session,
        trailing_stop_manager=trailing_stop_manager,
        order_router=order_router
    )
    
    # Initialize market data processor
    market_data_processor = MarketDataProcessor(
        db_session=db_session,
        redis_client=redis_client,
        position_manager=position_manager,
        trailing_stop_handler=trailing_stop_handler
    )
    
    logger.info("Order Processing Service started")
    logger.info("Starting market data processor for trailing stop monitoring...")
    
    # Main execution loop
    try:
        # Start market data processor in background
        # In production, this would run in a separate thread or process
        import threading
        processor_thread = threading.Thread(
            target=market_data_processor.start,
            daemon=True
        )
        processor_thread.start()
        
        while running:
            # Process other order execution tasks
            # This would typically listen to a message queue or Redis pub/sub
            time.sleep(1)
            
    except Exception as e:
        logger.error(f"Error in order processing service: {e}", exc_info=True)
    finally:
        logger.info("Order Processing Service shutting down")
        if market_data_processor:
            market_data_processor.stop()
        redis_client.close()
        db_session.close()


if __name__ == '__main__':
    main()
