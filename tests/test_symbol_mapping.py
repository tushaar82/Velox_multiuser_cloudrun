"""
Unit tests for symbol mapping service.
Tests symbol translation, CSV loading, and validation.
"""
import pytest
import tempfile
import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from shared.database.connection import Base
from shared.models.symbol_mapping import SymbolMapping, SymbolMappingCache
from shared.services.symbol_mapping_service import SymbolMappingService


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    from sqlalchemy import Table, Column, Integer, String, Numeric, DateTime, MetaData
    
    engine = create_engine('sqlite:///:memory:')
    metadata = MetaData()
    
    # Create only the symbol_mappings table for testing
    # SQLite doesn't support UUID, so we use String for id
    symbol_mappings_table = Table(
        'symbol_mappings',
        metadata,
        Column('id', String(36), primary_key=True),
        Column('standard_symbol', String(50), nullable=False),
        Column('broker_name', String(50), nullable=False),
        Column('broker_symbol', String(100), nullable=False),
        Column('broker_token', String(100), nullable=False),
        Column('exchange', String(10), nullable=False),
        Column('instrument_type', String(10), nullable=False),
        Column('lot_size', Integer, nullable=False, default=1),
        Column('tick_size', Numeric(10, 4), nullable=False, default=0.05),
        Column('created_at', DateTime, nullable=False),
        Column('updated_at', DateTime, nullable=False)
    )
    
    metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    yield session
    
    session.close()


@pytest.fixture
def symbol_service(db_session):
    """Create a SymbolMappingService instance with test database."""
    return SymbolMappingService(db_session)


@pytest.fixture
def sample_mappings(db_session):
    """Create sample symbol mappings in the database."""
    mappings = [
        SymbolMapping(
            standard_symbol="RELIANCE",
            broker_name="Angel One",
            broker_symbol="RELIANCE-EQ",
            broker_token="2885",
            exchange="NSE",
            instrument_type="EQ",
            lot_size=1,
            tick_size=0.05
        ),
        SymbolMapping(
            standard_symbol="TCS",
            broker_name="Angel One",
            broker_symbol="TCS-EQ",
            broker_token="11536",
            exchange="NSE",
            instrument_type="EQ",
            lot_size=1,
            tick_size=0.05
        ),
        SymbolMapping(
            standard_symbol="NIFTY50",
            broker_name="Angel One",
            broker_symbol="NIFTY",
            broker_token="99926000",
            exchange="NSE",
            instrument_type="INDEX",
            lot_size=1,
            tick_size=0.05
        ),
        SymbolMapping(
            standard_symbol="RELIANCE",
            broker_name="Upstox",
            broker_symbol="NSE_EQ|INE002A01018",
            broker_token="NSE_EQ|INE002A01018",
            exchange="NSE",
            instrument_type="EQ",
            lot_size=1,
            tick_size=0.05
        )
    ]
    
    for mapping in mappings:
        db_session.add(mapping)
    db_session.commit()
    
    return mappings


class TestSymbolTranslation:
    """Test symbol translation between standard and broker-specific formats."""
    
    def test_get_broker_symbol_from_standard(self, symbol_service, sample_mappings):
        """Test converting standard symbol to broker token."""
        broker_token = symbol_service.get_broker_symbol("Angel One", "RELIANCE")
        assert broker_token == "2885"
    
    def test_get_broker_symbol_different_broker(self, symbol_service, sample_mappings):
        """Test getting broker symbol for different broker."""
        broker_token = symbol_service.get_broker_symbol("Upstox", "RELIANCE")
        assert broker_token == "NSE_EQ|INE002A01018"
    
    def test_get_broker_symbol_not_found(self, symbol_service, sample_mappings):
        """Test getting broker symbol for non-existent mapping."""
        broker_token = symbol_service.get_broker_symbol("Angel One", "NONEXISTENT")
        assert broker_token is None
    
    def test_get_standard_symbol_from_broker_token(self, symbol_service, sample_mappings):
        """Test converting broker token to standard symbol."""
        standard_symbol = symbol_service.get_standard_symbol("Angel One", "2885")
        assert standard_symbol == "RELIANCE"
    
    def test_get_standard_symbol_from_broker_symbol(self, symbol_service, sample_mappings):
        """Test converting broker symbol to standard symbol."""
        standard_symbol = symbol_service.get_standard_symbol("Angel One", "RELIANCE-EQ")
        assert standard_symbol == "RELIANCE"
    
    def test_get_standard_symbol_not_found(self, symbol_service, sample_mappings):
        """Test getting standard symbol for non-existent broker token."""
        standard_symbol = symbol_service.get_standard_symbol("Angel One", "99999")
        assert standard_symbol is None
    
    def test_get_mapping_details(self, symbol_service, sample_mappings):
        """Test getting complete mapping details."""
        mapping = symbol_service.get_mapping_details("Angel One", "RELIANCE")
        
        assert mapping is not None
        assert mapping.standard_symbol == "RELIANCE"
        assert mapping.broker_token == "2885"
        assert mapping.exchange == "NSE"
        assert mapping.instrument_type == "EQ"
        assert mapping.lot_size == 1
        assert float(mapping.tick_size) == 0.05
    
    def test_validate_symbol_exists(self, symbol_service, sample_mappings):
        """Test validating an existing symbol."""
        is_valid = symbol_service.validate_symbol("Angel One", "RELIANCE")
        assert is_valid is True
    
    def test_validate_symbol_not_exists(self, symbol_service, sample_mappings):
        """Test validating a non-existent symbol."""
        is_valid = symbol_service.validate_symbol("Angel One", "NONEXISTENT")
        assert is_valid is False


class TestCSVLoading:
    """Test loading symbol mappings from CSV files."""
    
    def test_load_valid_csv(self, symbol_service):
        """Test loading a valid CSV file."""
        # Create temporary CSV file
        csv_content = """standard_symbol,broker_symbol,broker_token,exchange,instrument_type,lot_size,tick_size
INFY,INFY-EQ,1594,NSE,EQ,1,0.05
HDFCBANK,HDFCBANK-EQ,1333,NSE,EQ,1,0.05
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_path = f.name
        
        try:
            result = symbol_service.load_mappings_from_csv("Angel One", temp_path)
            
            assert result['success'] is True
            assert result['loaded'] == 2
            assert result['failed'] == 0
            
            # Verify mappings were loaded
            broker_token = symbol_service.get_broker_symbol("Angel One", "INFY")
            assert broker_token == "1594"
        
        finally:
            os.unlink(temp_path)
    
    def test_load_csv_with_invalid_rows(self, symbol_service):
        """Test loading CSV with some invalid rows."""
        csv_content = """standard_symbol,broker_symbol,broker_token,exchange,instrument_type,lot_size,tick_size
INFY,INFY-EQ,1594,NSE,EQ,1,0.05
INVALID,,,,,
HDFCBANK,HDFCBANK-EQ,1333,NSE,EQ,1,0.05
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_path = f.name
        
        try:
            result = symbol_service.load_mappings_from_csv("Angel One", temp_path)
            
            assert result['success'] is True
            assert result['loaded'] == 2
            assert result['failed'] == 1
        
        finally:
            os.unlink(temp_path)
    
    def test_load_csv_file_not_found(self, symbol_service):
        """Test loading non-existent CSV file."""
        result = symbol_service.load_mappings_from_csv("Angel One", "/nonexistent/file.csv")
        
        assert result['success'] is False
        assert 'File not found' in result['error']
    
    def test_load_csv_updates_existing_mapping(self, symbol_service, sample_mappings):
        """Test that loading CSV updates existing mappings."""
        # Create CSV with updated token for RELIANCE
        csv_content = """standard_symbol,broker_symbol,broker_token,exchange,instrument_type,lot_size,tick_size
RELIANCE,RELIANCE-EQ,9999,NSE,EQ,1,0.05
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            f.write(csv_content)
            temp_path = f.name
        
        try:
            result = symbol_service.load_mappings_from_csv("Angel One", temp_path)
            
            assert result['success'] is True
            assert result['loaded'] == 1
            
            # Verify mapping was updated
            broker_token = symbol_service.get_broker_symbol("Angel One", "RELIANCE")
            assert broker_token == "9999"
        
        finally:
            os.unlink(temp_path)


class TestMappingManagement:
    """Test mapping management operations."""
    
    def test_get_all_mappings(self, symbol_service, sample_mappings):
        """Test getting all mappings for a broker."""
        mappings = symbol_service.get_all_mappings("Angel One")
        
        assert len(mappings) == 3
        symbols = [m.standard_symbol for m in mappings]
        assert "RELIANCE" in symbols
        assert "TCS" in symbols
        assert "NIFTY50" in symbols
    
    def test_get_all_mappings_empty(self, symbol_service):
        """Test getting mappings for broker with no mappings."""
        mappings = symbol_service.get_all_mappings("NonExistentBroker")
        assert len(mappings) == 0
    
    def test_delete_mapping(self, symbol_service, sample_mappings):
        """Test deleting a symbol mapping."""
        success = symbol_service.delete_mapping("Angel One", "RELIANCE")
        assert success is True
        
        # Verify mapping was deleted
        broker_token = symbol_service.get_broker_symbol("Angel One", "RELIANCE")
        assert broker_token is None
    
    def test_delete_mapping_not_found(self, symbol_service, sample_mappings):
        """Test deleting non-existent mapping."""
        success = symbol_service.delete_mapping("Angel One", "NONEXISTENT")
        assert success is False
    
    def test_clear_broker_mappings(self, symbol_service, sample_mappings):
        """Test clearing all mappings for a broker."""
        success = symbol_service.clear_broker_mappings("Angel One")
        assert success is True
        
        # Verify all mappings were cleared
        mappings = symbol_service.get_all_mappings("Angel One")
        assert len(mappings) == 0
        
        # Verify other broker mappings still exist
        upstox_mappings = symbol_service.get_all_mappings("Upstox")
        assert len(upstox_mappings) == 1


class TestSymbolMappingCache:
    """Test in-memory cache functionality."""
    
    def test_cache_initialization(self):
        """Test cache initializes empty."""
        cache = SymbolMappingCache()
        assert len(cache.mappings) == 0
    
    def test_cache_set_and_get(self):
        """Test setting and getting from cache."""
        cache = SymbolMappingCache()
        mapping = SymbolMapping(
            standard_symbol="TEST",
            broker_name="TestBroker",
            broker_symbol="TEST-EQ",
            broker_token="123",
            exchange="NSE",
            instrument_type="EQ",
            lot_size=1,
            tick_size=0.05
        )
        
        cache.set_mapping("TestBroker", "TEST", mapping)
        retrieved = cache.get_mapping("TestBroker", "TEST")
        
        assert retrieved is not None
        assert retrieved.standard_symbol == "TEST"
        assert retrieved.broker_token == "123"
    
    def test_cache_get_broker_mappings(self):
        """Test getting all mappings for a broker from cache."""
        cache = SymbolMappingCache()
        
        mapping1 = SymbolMapping(
            standard_symbol="TEST1",
            broker_name="TestBroker",
            broker_symbol="TEST1-EQ",
            broker_token="123",
            exchange="NSE",
            instrument_type="EQ",
            lot_size=1,
            tick_size=0.05
        )
        
        mapping2 = SymbolMapping(
            standard_symbol="TEST2",
            broker_name="TestBroker",
            broker_symbol="TEST2-EQ",
            broker_token="456",
            exchange="NSE",
            instrument_type="EQ",
            lot_size=1,
            tick_size=0.05
        )
        
        cache.set_mapping("TestBroker", "TEST1", mapping1)
        cache.set_mapping("TestBroker", "TEST2", mapping2)
        
        broker_mappings = cache.get_broker_mappings("TestBroker")
        assert len(broker_mappings) == 2
        assert "TEST1" in broker_mappings
        assert "TEST2" in broker_mappings
    
    def test_cache_clear(self):
        """Test clearing entire cache."""
        cache = SymbolMappingCache()
        mapping = SymbolMapping(
            standard_symbol="TEST",
            broker_name="TestBroker",
            broker_symbol="TEST-EQ",
            broker_token="123",
            exchange="NSE",
            instrument_type="EQ",
            lot_size=1,
            tick_size=0.05
        )
        
        cache.set_mapping("TestBroker", "TEST", mapping)
        cache.clear()
        
        assert len(cache.mappings) == 0
        assert cache.get_mapping("TestBroker", "TEST") is None
    
    def test_cache_clear_broker(self):
        """Test clearing cache for specific broker."""
        cache = SymbolMappingCache()
        
        mapping1 = SymbolMapping(
            standard_symbol="TEST1",
            broker_name="Broker1",
            broker_symbol="TEST1-EQ",
            broker_token="123",
            exchange="NSE",
            instrument_type="EQ",
            lot_size=1,
            tick_size=0.05
        )
        
        mapping2 = SymbolMapping(
            standard_symbol="TEST2",
            broker_name="Broker2",
            broker_symbol="TEST2-EQ",
            broker_token="456",
            exchange="NSE",
            instrument_type="EQ",
            lot_size=1,
            tick_size=0.05
        )
        
        cache.set_mapping("Broker1", "TEST1", mapping1)
        cache.set_mapping("Broker2", "TEST2", mapping2)
        
        cache.clear_broker("Broker1")
        
        assert cache.get_mapping("Broker1", "TEST1") is None
        assert cache.get_mapping("Broker2", "TEST2") is not None
