"""
Strategy Execution Service Entry Point

Background service that executes trading strategies.
"""
import logging
import time
import signal
import sys
from redis import Redis

from shared.utils.logging_config import setup_logging
from shared.config.settings import get_settings
from shared.database.connection import get_db_session
from strategy_workers.strategy_orchestrator import StrategyOrchestrator
from strategy_workers.strategy_plugin_manager import StrategyPluginManager
from strategy_workers.strategy_state_manager import StrategyStateManager
from strategy_workers.multi_timeframe_provider import MultiTimeframeDataProvider

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
    
    # Initialize components
    plugin_manager = StrategyPluginManager()
    state_manager = StrategyStateManager(redis_client)
    data_provider = MultiTimeframeDataProvider(redis_client)
    
    # Initialize orchestrator
    orchestrator = StrategyOrchestrator(
        redis_client=redis_client,
        plugin_manager=plugin_manager,
        state_manager=state_manager,
        data_provider=data_provider
    )
    
    logger.info("Strategy Execution Service started")
    
    # Main execution loop
    try:
        while running:
            # Process strategy execution tasks
            # This would typically listen to a message queue or Redis pub/sub
            time.sleep(1)
            
    except Exception as e:
        logger.error(f"Error in strategy execution service: {e}", exc_info=True)
    finally:
        logger.info("Strategy Execution Service shutting down")
        redis_client.close()


if __name__ == '__main__':
    main()
