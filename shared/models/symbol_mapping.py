"""
Symbol mapping data models.
Implements SymbolMapping table for translating between standard NSE symbols 
and broker-specific symbol tokens.
"""
import uuid
from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass

from sqlalchemy import (
    Column, DateTime, Integer, Numeric, String, Index
)
from sqlalchemy.dialects.postgresql import UUID

from shared.database.connection import Base


class SymbolMapping(Base):
    """Symbol mapping model for broker symbol translation."""
    
    __tablename__ = "symbol_mappings"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    standard_symbol = Column(String(50), nullable=False)
    broker_name = Column(String(50), nullable=False)
    broker_symbol = Column(String(100), nullable=False)
    broker_token = Column(String(100), nullable=False)
    exchange = Column(String(10), nullable=False)
    instrument_type = Column(String(10), nullable=False)
    lot_size = Column(Integer, nullable=False, default=1)
    tick_size = Column(Numeric(10, 4), nullable=False, default=0.05)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index("idx_symbol_mappings_broker", "broker_name", "standard_symbol", unique=True),
        Index("idx_symbol_mappings_token", "broker_name", "broker_token"),
    )
    
    def __repr__(self) -> str:
        return (
            f"<SymbolMapping(standard_symbol={self.standard_symbol}, "
            f"broker={self.broker_name}, token={self.broker_token})>"
        )


@dataclass
class SymbolMappingCache:
    """In-memory cache for symbol mappings."""
    
    # {broker_name: {standard_symbol: SymbolMapping}}
    mappings: Dict[str, Dict[str, SymbolMapping]]
    last_updated: datetime
    
    def __init__(self):
        self.mappings = {}
        self.last_updated = datetime.utcnow()
    
    def get_mapping(self, broker_name: str, standard_symbol: str) -> Optional[SymbolMapping]:
        """Get symbol mapping from cache."""
        broker_mappings = self.mappings.get(broker_name, {})
        return broker_mappings.get(standard_symbol)
    
    def set_mapping(self, broker_name: str, standard_symbol: str, mapping: SymbolMapping) -> None:
        """Set symbol mapping in cache."""
        if broker_name not in self.mappings:
            self.mappings[broker_name] = {}
        self.mappings[broker_name][standard_symbol] = mapping
        self.last_updated = datetime.utcnow()
    
    def get_broker_mappings(self, broker_name: str) -> Dict[str, SymbolMapping]:
        """Get all mappings for a broker."""
        return self.mappings.get(broker_name, {})
    
    def clear(self) -> None:
        """Clear all cached mappings."""
        self.mappings = {}
        self.last_updated = datetime.utcnow()
    
    def clear_broker(self, broker_name: str) -> None:
        """Clear mappings for a specific broker."""
        if broker_name in self.mappings:
            del self.mappings[broker_name]
            self.last_updated = datetime.utcnow()
