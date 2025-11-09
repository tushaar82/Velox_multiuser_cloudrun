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

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Global flag for graceful shutdown
running = True


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully"""
    global running
    logger.info(f"Received signal {sig}, initiating graceful shutdown...")
    running = False


def main():
    """Main execution loop"""
    global running
    
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
    position_manager = PositionManager(db_session, redis_client)
    trailing_stop_manager = TrailingStopManager(db_session, redis_client)
    
    # Initialize order router
    order_router = OrderRouter(
        db_session=db_session,
        symbol_mapping_service=symbol_mapping_service,
        broker_connectors={},  # Broker connectors would be initialized here
        paper_trading_simulator=paper_simulator
    )
    
    logger.info("Order Processing Service started")
    
    # Main execution loop
    try:
        while running:
            # Process order execution tasks
            # This would typically listen to a message queue or Redis pub/sub
            time.sleep(1)
            
    except Exception as e:
        logger.error(f"Error in order processing service: {e}", exc_info=True)
    finally:
        logger.info("Order Processing Service shutting down")
        redis_client.close()
        db_session.close()


if __name__ == '__main__':
    main()
