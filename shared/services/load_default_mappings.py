"""
Script to load default symbol mappings on first startup.
"""
import logging
import os
from pathlib import Path

from shared.database.connection import get_db_session
from shared.services.symbol_mapping_service import SymbolMappingService
from shared.models.symbol_mapping import SymbolMapping


logger = logging.getLogger(__name__)


def load_default_angel_one_mappings() -> bool:
    """
    Load default Angel One symbol mappings if not already loaded.
    
    Returns:
        True if mappings were loaded or already exist, False on error
    """
    try:
        db = next(get_db_session())
        service = SymbolMappingService(db)
        
        # Check if Angel One mappings already exist
        existing_mappings = db.query(SymbolMapping).filter(
            SymbolMapping.broker_name == "Angel One"
        ).count()
        
        if existing_mappings > 0:
            logger.info(f"Angel One mappings already loaded ({existing_mappings} symbols)")
            return True
        
        # Load from CSV file
        csv_path = Path(__file__).parent.parent / "data" / "angel_one_symbol_mappings.csv"
        
        if not csv_path.exists():
            logger.error(f"Default mappings CSV not found: {csv_path}")
            return False
        
        logger.info(f"Loading default Angel One mappings from {csv_path}")
        result = service.load_mappings_from_csv("Angel One", str(csv_path))
        
        if result['success']:
            logger.info(
                f"Successfully loaded {result['loaded']} Angel One symbol mappings "
                f"({result['failed']} failed)"
            )
            return True
        else:
            logger.error(f"Failed to load default mappings: {result.get('error', 'Unknown error')}")
            return False
    
    except Exception as e:
        logger.error(f"Error loading default mappings: {e}")
        return False
    finally:
        if 'db' in locals():
            db.close()


def initialize_symbol_mappings() -> None:
    """
    Initialize symbol mappings for all supported brokers.
    This should be called during application startup.
    """
    logger.info("Initializing symbol mappings...")
    
    # Load Angel One mappings
    load_default_angel_one_mappings()
    
    # Add other brokers here as they are implemented
    # load_default_upstox_mappings()
    # load_default_fyers_mappings()
    
    logger.info("Symbol mapping initialization complete")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Load default mappings
    initialize_symbol_mappings()
