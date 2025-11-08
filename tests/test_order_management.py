"""
Unit tests for order management and routing.
"""
import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from shared.database.connection import Base
from shared.models.order import Order, OrderData, OrderStatus, OrderSide, OrderType, TradingMode
from shared.models.trade import Trade, TradeData
from shared.models.broker_connection import BrokerConnection
from shared.models.symbol_mapping import SymbolMapping
from shared.services.symbol_mapping_service import SymbolMappingService
from shared.brokers.base import IBrokerConnector, BrokerOrder, BrokerOrderResponse
from order_processor.paper_trading_simulator import PaperTradingSimulator
from order_processor.order_router import OrderRouter, OrderValidationError
import uuid


# Test database setup
@pytest.fixture(scope='function')
def db_session():
    """Create a test database session."""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture
def paper_simulator():
    """Create paper trading simulator."""
    return PaperTradingSimulator(slippage=0.0005, commission_rate=0.0003)


@pytest.fixture
def mock_broker_connector():
    """Create mock broker connector."""
    connector = Mock(spec=IBrokerConnector)
    connector.is_connected.return_value = True
    connector.place_order.return_value = BrokerOrderResponse(
        broker_order_id='BROKER123',
        status='open',
        message='Order placed successfully'
    )
    return connector


@pytest.fixture
def symbol_mapping_service(db_session):
    """Create symbol mapping service with test data."""
    # Add test symbol mapping
    mapping = SymbolMapping(
        standard_symbol='RELIANCE',
        broker_name='Test Broker',
        broker_symbol='RELIANCE-EQ',
        broker_token='2885',
        exchange='NSE',
        instrument_type='EQ',
        lot_size=1,
        tick_size=0.05
    )
    db_session.add(mapping)
    db_session.commit()
    
    return SymbolMappingService(db_session)


@pytest.fixture
def order_router(db_session, symbol_mapping_service, mock_broker_connector, paper_simulator):
    """Create order router with dependencies."""
    broker_connectors = {'Test Broker': mock_broker_connector}
    return OrderRouter(
        db_session,
        symbol_mapping_service,
        broker_connectors,
        paper_simulator
    )


class TestPaperTradingSimulator:
    """Tests for paper trading simulator."""
    
    def test_market_order_buy_with_slippage(self, paper_simulator):
        """Test market buy order applies positive slippage."""
        order = OrderData(
            id=str(uuid.uuid4()),
            account_id=str(uuid.uuid4()),
            strategy_id=None,
            symbol='RELIANCE',
            side=OrderSide.BUY,
            quantity=10,
            order_type='market',
            price=None,
            stop_price=None,
            trading_mode=TradingMode.PAPER,
            status=OrderStatus.PENDING,
            filled_quantity=0,
            average_price=None,
            broker_order_id=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        current_price = 2450.00
        updated_order, trade = paper_simulator.simulate_market_order(order, current_price)
        
        # Check slippage applied (buy price should be higher)
        expected_price = current_price * (1 + paper_simulator.slippage)
        assert trade.price == round(expected_price, 2)
        assert updated_order.status == OrderStatus.FILLED
        assert updated_order.filled_quantity == 10
        assert trade.commission > 0
    
    def test_market_order_sell_with_slippage(self, paper_simulator):
        """Test market sell order applies negative slippage."""
        order = OrderData(
            id=str(uuid.uuid4()),
            account_id=str(uuid.uuid4()),
            strategy_id=None,
            symbol='RELIANCE',
            side=OrderSide.SELL,
            quantity=10,
            order_type='market',
            price=None,
            stop_price=None,
            trading_mode=TradingMode.PAPER,
            status=OrderStatus.PENDING,
            filled_quantity=0,
            average_price=None,
            broker_order_id=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        current_price = 2450.00
        updated_order, trade = paper_simulator.simulate_market_order(order, current_price)
        
        # Check slippage applied (sell price should be lower)
        expected_price = current_price * (1 - paper_simulator.slippage)
        assert trade.price == round(expected_price, 2)
        assert updated_order.status == OrderStatus.FILLED
    
    def test_limit_order_fills_when_price_reached(self, paper_simulator):
        """Test limit buy order fills when market price reaches limit."""
        order = OrderData(
            id=str(uuid.uuid4()),
            account_id=str(uuid.uuid4()),
            strategy_id=None,
            symbol='RELIANCE',
            side=OrderSide.BUY,
            quantity=10,
            order_type='limit',
            price=2450.00,
            stop_price=None,
            trading_mode=TradingMode.PAPER,
            status=OrderStatus.PENDING,
            filled_quantity=0,
            average_price=None,
            broker_order_id=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Price at limit - should fill
        result = paper_simulator.simulate_limit_order(order, 2450.00)
        assert result is not None
        updated_order, trade = result
        assert updated_order.status == OrderStatus.FILLED
        assert trade.price == 2450.00
    
    def test_limit_order_pending_when_price_not_reached(self, paper_simulator):
        """Test limit buy order stays pending when price not reached."""
        order = OrderData(
            id=str(uuid.uuid4()),
            account_id=str(uuid.uuid4()),
            strategy_id=None,
            symbol='RELIANCE',
            side=OrderSide.BUY,
            quantity=10,
            order_type='limit',
            price=2450.00,
            stop_price=None,
            trading_mode=TradingMode.PAPER,
            status=OrderStatus.PENDING,
            filled_quantity=0,
            average_price=None,
            broker_order_id=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        # Price above limit - should not fill
        result = paper_simulator.simulate_limit_order(order, 2460.00)
        assert result is None
    
    def test_commission_calculation(self, paper_simulator):
        """Test commission is calculated correctly."""
        order = OrderData(
            id=str(uuid.uuid4()),
            account_id=str(uuid.uuid4()),
            strategy_id=None,
            symbol='RELIANCE',
            side=OrderSide.BUY,
            quantity=100,
            order_type='market',
            price=None,
            stop_price=None,
            trading_mode=TradingMode.PAPER,
            status=OrderStatus.PENDING,
            filled_quantity=0,
            average_price=None,
            broker_order_id=None,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        current_price = 2450.00
        updated_order, trade = paper_simulator.simulate_market_order(order, current_price)
        
        # Calculate expected commission
        trade_value = trade.price * 100
        expected_commission = trade_value * paper_simulator.commission_rate
        assert trade.commission == round(expected_commission, 2)


class TestOrderRouter:
    """Tests for order router."""
    
    def test_paper_order_submission(self, order_router, db_session):
        """Test paper trading order submission."""
        account_id = str(uuid.uuid4())
        
        order = order_router.submit_order(
            account_id=account_id,
            symbol='RELIANCE',
            side=OrderSide.BUY,
            quantity=10,
            order_type='market',
            trading_mode=TradingMode.PAPER,
            current_market_price=2450.00
        )
        
        assert order.status == OrderStatus.FILLED
        assert order.trading_mode == TradingMode.PAPER
        assert order.filled_quantity == 10
        
        # Verify order saved to database
        db_order = db_session.query(Order).filter(Order.id == uuid.UUID(order.id)).first()
        assert db_order is not None
        assert db_order.status == OrderStatus.FILLED
    
    def test_live_order_submission_with_symbol_mapping(self, order_router, db_session, mock_broker_connector):
        """Test live order submission with symbol translation."""
        account_id = uuid.uuid4()
        
        # Add broker connection
        broker_conn = BrokerConnection(
            id=uuid.uuid4(),
            account_id=account_id,
            broker_name='Test Broker',
            credentials_encrypted='encrypted_creds',
            is_connected=True
        )
        db_session.add(broker_conn)
        db_session.commit()
        
        order = order_router.submit_order(
            account_id=str(account_id),
            symbol='RELIANCE',
            side=OrderSide.BUY,
            quantity=10,
            order_type='market',
            trading_mode=TradingMode.LIVE
        )
        
        assert order.status == OrderStatus.SUBMITTED
        assert order.broker_order_id == 'BROKER123'
        
        # Verify broker connector was called with translated symbol
        mock_broker_connector.place_order.assert_called_once()
        broker_order = mock_broker_connector.place_order.call_args[0][0]
        assert broker_order.symbol == '2885'  # Broker token
    
    def test_order_validation_negative_quantity(self, order_router):
        """Test order validation rejects negative quantity."""
        with pytest.raises(OrderValidationError, match="Quantity must be positive"):
            order_router.submit_order(
                account_id=str(uuid.uuid4()),
                symbol='RELIANCE',
                side=OrderSide.BUY,
                quantity=-10,
                order_type='market',
                trading_mode=TradingMode.PAPER,
                current_market_price=2450.00
            )
    
    def test_order_validation_limit_order_requires_price(self, order_router):
        """Test limit order validation requires price."""
        with pytest.raises(OrderValidationError, match="limit order requires price"):
            order_router.submit_order(
                account_id=str(uuid.uuid4()),
                symbol='RELIANCE',
                side=OrderSide.BUY,
                quantity=10,
                order_type='limit',
                trading_mode=TradingMode.PAPER,
                current_market_price=2450.00
            )
    
    def test_cancel_paper_order(self, order_router, db_session):
        """Test cancelling a paper trading order."""
        account_id = str(uuid.uuid4())
        
        # Submit limit order that stays pending
        order = order_router.submit_order(
            account_id=account_id,
            symbol='RELIANCE',
            side=OrderSide.BUY,
            quantity=10,
            order_type='limit',
            price=2400.00,
            trading_mode=TradingMode.PAPER,
            current_market_price=2450.00
        )
        
        assert order.status == OrderStatus.SUBMITTED
        
        # Cancel order
        success = order_router.cancel_order(order.id)
        assert success is True
        
        # Verify order status updated
        db_order = db_session.query(Order).filter(Order.id == uuid.UUID(order.id)).first()
        assert db_order.status == OrderStatus.CANCELLED
    
    def test_separation_of_paper_and_live_orders(self, order_router, db_session):
        """Test paper and live orders are tracked separately."""
        account_id = str(uuid.uuid4())
        
        # Submit paper order
        paper_order = order_router.submit_order(
            account_id=account_id,
            symbol='RELIANCE',
            side=OrderSide.BUY,
            quantity=10,
            order_type='market',
            trading_mode=TradingMode.PAPER,
            current_market_price=2450.00
        )
        
        # Get paper orders
        paper_orders = order_router.get_orders(account_id, TradingMode.PAPER)
        assert len(paper_orders) == 1
        assert paper_orders[0].trading_mode == TradingMode.PAPER
        
        # Get live orders
        live_orders = order_router.get_orders(account_id, TradingMode.LIVE)
        assert len(live_orders) == 0


class TestSymbolTranslation:
    """Tests for symbol mapping in order flow."""
    
    def test_symbol_translation_in_order_submission(self, order_router, db_session, mock_broker_connector):
        """Test symbol is translated before sending to broker."""
        account_id = uuid.uuid4()
        
        # Add broker connection
        broker_conn = BrokerConnection(
            id=uuid.uuid4(),
            account_id=account_id,
            broker_name='Test Broker',
            credentials_encrypted='encrypted_creds',
            is_connected=True
        )
        db_session.add(broker_conn)
        db_session.commit()
        
        # Submit order with standard symbol
        order = order_router.submit_order(
            account_id=str(account_id),
            symbol='RELIANCE',  # Standard symbol
            side=OrderSide.BUY,
            quantity=10,
            order_type='market',
            trading_mode=TradingMode.LIVE
        )
        
        # Verify broker received translated symbol
        broker_order = mock_broker_connector.place_order.call_args[0][0]
        assert broker_order.symbol == '2885'  # Broker token
        
        # Verify order stored with standard symbol
        db_order = db_session.query(Order).filter(Order.id == uuid.UUID(order.id)).first()
        assert db_order.symbol == 'RELIANCE'
    
    def test_missing_symbol_mapping_rejects_order(self, order_router, db_session):
        """Test order is rejected if symbol mapping not found."""
        account_id = uuid.uuid4()
        
        # Add broker connection
        broker_conn = BrokerConnection(
            id=uuid.uuid4(),
            account_id=account_id,
            broker_name='Test Broker',
            credentials_encrypted='encrypted_creds',
            is_connected=True
        )
        db_session.add(broker_conn)
        db_session.commit()
        
        # Submit order with unmapped symbol
        with pytest.raises(OrderValidationError, match="not supported by broker"):
            order_router.submit_order(
                account_id=str(account_id),
                symbol='UNKNOWN_SYMBOL',
                side=OrderSide.BUY,
                quantity=10,
                order_type='market',
                trading_mode=TradingMode.LIVE
            )


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
