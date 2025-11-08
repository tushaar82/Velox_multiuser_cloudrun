"""
Symbol mapping service wrapper for API gateway.
"""
import logging
from typing import Optional, List, Dict, Any

from shared.database.connection import get_db_session
from shared.services.symbol_mapping_service import SymbolMappingService
from shared.models.symbol_mapping import SymbolMapping


logger = logging.getLogger(__name__)


class SymbolMappingServiceAPI:
    """API wrapper for symbol mapping service."""
    
    def __init__(self):
        """Initialize the service with a database session."""
        self.db = next(get_db_session())
        self.service = SymbolMappingService(self.db)
    
    def __del__(self):
        """Close database session on cleanup."""
        if hasattr(self, 'db'):
            self.db.close()
    
    def get_standard_symbol(self, broker_name: str, broker_symbol: str) -> Optional[str]:
        """Convert broker symbol to standard symbol."""
        return self.service.get_standard_symbol(broker_name, broker_symbol)
    
    def get_broker_symbol(self, broker_name: str, standard_symbol: str) -> Optional[str]:
        """Convert standard symbol to broker token."""
        return self.service.get_broker_symbol(broker_name, standard_symbol)
    
    def get_mapping_details(self, broker_name: str, standard_symbol: str) -> Optional[SymbolMapping]:
        """Get complete mapping details."""
        return self.service.get_mapping_details(broker_name, standard_symbol)
    
    def validate_symbol(self, broker_name: str, standard_symbol: str) -> bool:
        """Validate if symbol exists in mapping."""
        return self.service.validate_symbol(broker_name, standard_symbol)
    
    def load_mappings_from_csv(self, broker_name: str, csv_file_path: str) -> Dict[str, Any]:
        """Load symbol mappings from CSV file."""
        return self.service.load_mappings_from_csv(broker_name, csv_file_path)
    
    def get_all_mappings(self, broker_name: str) -> List[SymbolMapping]:
        """Get all mappings for a broker."""
        return self.service.get_all_mappings(broker_name)
    
    def delete_mapping(self, broker_name: str, standard_symbol: str) -> bool:
        """Delete a symbol mapping."""
        return self.service.delete_mapping(broker_name, standard_symbol)
    
    def clear_broker_mappings(self, broker_name: str) -> bool:
        """Clear all mappings for a broker."""
        return self.service.clear_broker_mappings(broker_name)
