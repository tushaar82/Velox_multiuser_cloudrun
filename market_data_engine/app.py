"""
Market Data Engine Entry Point

Main application that runs the market data engine service.
"""
import logging
import signal
import sys
import time

from shared.utils.logging_config import setup_logging
from shared.config.settings import get_settings
from market_data_engine.service import MarketDataEngine

# Setup logging
setup_logging('market_data_engine')
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

# Global flag for graceful shutdown
running = True


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully"""
    global running
    logger.info("Shutdown signal received, stopping market data engine...")
    running = False


def main():
    """Main entry point for market data engine"""
    global running
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize market data engine (it initializes all components internally)
        engine = MarketDataEngine(
            feed_type='simulated',
            feed_config={}
        )
        
        logger.info("Market Data Engine initialized successfully")
        
        # Start the engine
        engine.start()
        
        # Keep running until shutdown signal
        while running:
            time.sleep(1)
        
        # Stop the engine
        engine.stop()
        logger.info("Market Data Engine stopped")
        
    except Exception as e:
        logger.error(f"Error in market data engine: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
