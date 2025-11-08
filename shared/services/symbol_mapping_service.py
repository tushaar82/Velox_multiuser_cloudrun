"""
Symbol Mapping Service for translating between standard NSE symbols 
and broker-specific symbol tokens.
"""
import csv
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from shared.models.symbol_mapping import SymbolMapping, SymbolMappingCache
from shared.redis.connection import get_redis_client


logger = logging.getLogger(__name__)


class SymbolMappingService:
    """Service for managing symbol mappings between standard and broker-specific formats."""
    
    def __init__(self, db_session: Session):
        """
        Initialize the symbol mapping service.
        
        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.cache = SymbolMappingCache()
        try:
            self.redis_client = get_redis_client()
        except RuntimeError:
            # Redis not initialized (e.g., in tests), continue without it
            self.redis_client = None
            logger.warning("Redis not available, symbol mapping will use in-memory cache only")
        self._load_cache_from_db()
    
    def _load_cache_from_db(self) -> None:
        """Load all symbol mappings from database into in-memory cache."""
        try:
            mappings = self.db.query(SymbolMapping).all()
            for mapping in mappings:
                self.cache.set_mapping(
                    mapping.broker_name,
                    mapping.standard_symbol,
                    mapping
                )
            logger.info(f"Loaded {len(mappings)} symbol mappings into cache")
        except Exception as e:
            logger.error(f"Failed to load symbol mappings from database: {e}")
    
    def get_standard_symbol(self, broker_name: str, broker_symbol: str) -> Optional[str]:
        """
        Convert broker-specific symbol to standard NSE symbol.
        
        Args:
            broker_name: Name of the broker (e.g., "Angel One")
            broker_symbol: Broker-specific symbol or token
            
        Returns:
            Standard symbol if found, None otherwise
        """
        # Try to find by broker_symbol first
        broker_mappings = self.cache.get_broker_mappings(broker_name)
        for standard_symbol, mapping in broker_mappings.items():
            if mapping.broker_symbol == broker_symbol or mapping.broker_token == broker_symbol:
                return standard_symbol
        
        # Fallback to Redis
        redis_key = f"symbol_mapping:{broker_name}:{broker_symbol}"
        try:
            if self.redis_client:
                cached_value = self.redis_client.get(redis_key)
                if cached_value:
                    return cached_value.decode('utf-8')
        except Exception as e:
            logger.warning(f"Redis lookup failed for {broker_symbol}: {e}")
        
        # Fallback to database
        try:
            mapping = self.db.query(SymbolMapping).filter(
                SymbolMapping.broker_name == broker_name,
                (SymbolMapping.broker_symbol == broker_symbol) | 
                (SymbolMapping.broker_token == broker_symbol)
            ).first()
            
            if mapping:
                # Update cache
                self.cache.set_mapping(broker_name, mapping.standard_symbol, mapping)
                # Update Redis
                if self.redis_client:
                    try:
                        self.redis_client.setex(redis_key, 3600, mapping.standard_symbol)
                    except Exception as e:
                        logger.warning(f"Failed to cache in Redis: {e}")
                return mapping.standard_symbol
        except Exception as e:
            logger.error(f"Database lookup failed for {broker_symbol}: {e}")
        
        return None
    
    def get_broker_symbol(self, broker_name: str, standard_symbol: str) -> Optional[str]:
        """
        Convert standard NSE symbol to broker-specific symbol token.
        
        Args:
            broker_name: Name of the broker (e.g., "Angel One")
            standard_symbol: Standard NSE symbol
            
        Returns:
            Broker-specific token if found, None otherwise
        """
        # Try in-memory cache first
        mapping = self.cache.get_mapping(broker_name, standard_symbol)
        if mapping:
            return mapping.broker_token
        
        # Fallback to Redis
        redis_key = f"symbol_mapping:{broker_name}:{standard_symbol}"
        try:
            if self.redis_client:
                cached_value = self.redis_client.get(redis_key)
                if cached_value:
                    return cached_value.decode('utf-8')
        except Exception as e:
            logger.warning(f"Redis lookup failed for {standard_symbol}: {e}")
        
        # Fallback to database
        try:
            mapping = self.db.query(SymbolMapping).filter(
                SymbolMapping.broker_name == broker_name,
                SymbolMapping.standard_symbol == standard_symbol
            ).first()
            
            if mapping:
                # Update cache
                self.cache.set_mapping(broker_name, standard_symbol, mapping)
                # Update Redis
                if self.redis_client:
                    try:
                        self.redis_client.setex(redis_key, 3600, mapping.broker_token)
                    except Exception as e:
                        logger.warning(f"Failed to cache in Redis: {e}")
                return mapping.broker_token
        except Exception as e:
            logger.error(f"Database lookup failed for {standard_symbol}: {e}")
        
        return None
    
    def get_mapping_details(self, broker_name: str, standard_symbol: str) -> Optional[SymbolMapping]:
        """
        Get complete symbol mapping details.
        
        Args:
            broker_name: Name of the broker
            standard_symbol: Standard NSE symbol
            
        Returns:
            SymbolMapping object if found, None otherwise
        """
        # Try in-memory cache first
        mapping = self.cache.get_mapping(broker_name, standard_symbol)
        if mapping:
            return mapping
        
        # Fallback to database
        try:
            mapping = self.db.query(SymbolMapping).filter(
                SymbolMapping.broker_name == broker_name,
                SymbolMapping.standard_symbol == standard_symbol
            ).first()
            
            if mapping:
                # Update cache
                self.cache.set_mapping(broker_name, standard_symbol, mapping)
            
            return mapping
        except Exception as e:
            logger.error(f"Failed to get mapping details: {e}")
            return None
    
    def validate_symbol(self, broker_name: str, standard_symbol: str) -> bool:
        """
        Check if a symbol exists in the mapping for a specific broker.
        
        Args:
            broker_name: Name of the broker
            standard_symbol: Standard NSE symbol
            
        Returns:
            True if symbol exists, False otherwise
        """
        return self.get_broker_symbol(broker_name, standard_symbol) is not None
    
    def load_mappings_from_csv(self, broker_name: str, csv_file_path: str) -> Dict[str, Any]:
        """
        Load symbol mappings from a CSV file.
        
        CSV format:
        standard_symbol,broker_symbol,broker_token,exchange,instrument_type,lot_size,tick_size
        
        Args:
            broker_name: Name of the broker
            csv_file_path: Path to the CSV file
            
        Returns:
            Dictionary with success status and statistics
        """
        if not Path(csv_file_path).exists():
            logger.error(f"CSV file not found: {csv_file_path}")
            return {
                "success": False,
                "error": "File not found",
                "loaded": 0,
                "failed": 0
            }
        
        loaded_count = 0
        failed_count = 0
        errors = []
        
        try:
            with open(csv_file_path, 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                
                for row in reader:
                    try:
                        # Validate required fields
                        required_fields = [
                            'standard_symbol', 'broker_symbol', 'broker_token',
                            'exchange', 'instrument_type', 'lot_size', 'tick_size'
                        ]
                        
                        if not all(field in row for field in required_fields):
                            failed_count += 1
                            errors.append(f"Missing required fields in row: {row}")
                            continue
                        
                        # Create or update mapping
                        mapping = self.db.query(SymbolMapping).filter(
                            SymbolMapping.broker_name == broker_name,
                            SymbolMapping.standard_symbol == row['standard_symbol']
                        ).first()
                        
                        if mapping:
                            # Update existing mapping
                            mapping.broker_symbol = row['broker_symbol']
                            mapping.broker_token = row['broker_token']
                            mapping.exchange = row['exchange']
                            mapping.instrument_type = row['instrument_type']
                            mapping.lot_size = int(row['lot_size'])
                            mapping.tick_size = float(row['tick_size'])
                        else:
                            # Create new mapping
                            mapping = SymbolMapping(
                                standard_symbol=row['standard_symbol'],
                                broker_name=broker_name,
                                broker_symbol=row['broker_symbol'],
                                broker_token=row['broker_token'],
                                exchange=row['exchange'],
                                instrument_type=row['instrument_type'],
                                lot_size=int(row['lot_size']),
                                tick_size=float(row['tick_size'])
                            )
                            self.db.add(mapping)
                        
                        self.db.commit()
                        
                        # Update cache
                        self.cache.set_mapping(broker_name, row['standard_symbol'], mapping)
                        
                        loaded_count += 1
                        
                    except (ValueError, IntegrityError) as e:
                        self.db.rollback()
                        failed_count += 1
                        errors.append(f"Failed to load row {row.get('standard_symbol', 'unknown')}: {str(e)}")
                        logger.error(f"Failed to load mapping: {e}")
            
            logger.info(f"Loaded {loaded_count} mappings, {failed_count} failed")
            
            return {
                "success": True,
                "loaded": loaded_count,
                "failed": failed_count,
                "errors": errors[:10]  # Return first 10 errors
            }
            
        except Exception as e:
            logger.error(f"Failed to load CSV file: {e}")
            return {
                "success": False,
                "error": str(e),
                "loaded": loaded_count,
                "failed": failed_count
            }
    
    def get_all_mappings(self, broker_name: str) -> List[SymbolMapping]:
        """
        Get all symbol mappings for a specific broker.
        
        Args:
            broker_name: Name of the broker
            
        Returns:
            List of SymbolMapping objects
        """
        try:
            mappings = self.db.query(SymbolMapping).filter(
                SymbolMapping.broker_name == broker_name
            ).all()
            return mappings
        except Exception as e:
            logger.error(f"Failed to get all mappings: {e}")
            return []
    
    def delete_mapping(self, broker_name: str, standard_symbol: str) -> bool:
        """
        Delete a symbol mapping.
        
        Args:
            broker_name: Name of the broker
            standard_symbol: Standard NSE symbol
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            mapping = self.db.query(SymbolMapping).filter(
                SymbolMapping.broker_name == broker_name,
                SymbolMapping.standard_symbol == standard_symbol
            ).first()
            
            if mapping:
                self.db.delete(mapping)
                self.db.commit()
                
                # Remove from cache
                broker_mappings = self.cache.mappings.get(broker_name, {})
                if standard_symbol in broker_mappings:
                    del broker_mappings[standard_symbol]
                
                # Remove from Redis
                if self.redis_client:
                    try:
                        redis_key = f"symbol_mapping:{broker_name}:{standard_symbol}"
                        self.redis_client.delete(redis_key)
                    except Exception as e:
                        logger.warning(f"Failed to delete from Redis: {e}")
                
                logger.info(f"Deleted mapping: {broker_name} - {standard_symbol}")
                return True
            
            return False
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to delete mapping: {e}")
            return False
    
    def clear_broker_mappings(self, broker_name: str) -> bool:
        """
        Clear all mappings for a specific broker.
        
        Args:
            broker_name: Name of the broker
            
        Returns:
            True if cleared successfully, False otherwise
        """
        try:
            self.db.query(SymbolMapping).filter(
                SymbolMapping.broker_name == broker_name
            ).delete()
            self.db.commit()
            
            # Clear from cache
            self.cache.clear_broker(broker_name)
            
            logger.info(f"Cleared all mappings for broker: {broker_name}")
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to clear broker mappings: {e}")
            return False
