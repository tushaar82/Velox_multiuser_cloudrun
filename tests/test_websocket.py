"""
Integration tests for WebSocket service.
Tests WebSocket connection, authentication, market data subscriptions, and broadcasting.
"""
import pytest
import json
import uuid
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from shared.database.connection import Base
from shared.models import User, UserRole, UserAccount, AccountAccess
from shared.utils.jwt import generate_token
from shared.utils.password import hash_password
from websocket_service.websocket_server import app, socketio
from websocket_service.room_manager import RoomManager
from market_data_engine.models import Tick, Candle, IndicatorValue
from shared.models.position import PositionData, PositionSide
from shared.models.order import OrderData, OrderStatus, OrderSide, TradingMode
from shared.models.notification import NotificationData, NotificationType, NotificationSeverity


@pytest.fixture
def db_session():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    yield session
    
    session.close()


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(
        email="test@example.com",
        password_hash=hash_password("TestPass123!"),
        role=UserRole.TRADER
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    return user


@pytest.fixture
def test_account(db_session, test_user):
    """Create a test account."""
    account = UserAccount(
        trader_id=test_user.id,
        name="Test Account"
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    
    # Grant access to user
    access = AccountAccess(
        account_id=account.id,
        user_id=test_user.id,
        role='trader'
    )
    db_session.add(access)
    db_session.commit()
    
    return account


@pytest.fixture
def auth_token(test_user):
    """Generate JWT token for test user."""
    return generate_token(test_user.id, test_user.role.value)


@pytest.fixture
def socketio_client(auth_token):
    """Create a SocketIO test client with authentication."""
    client = socketio.test_client(
        app,
        query_string=f'token={auth_token}',
        flask_test_client=app.test_client()
    )
    return client


class TestWebSocketConnection:
    """Test WebSocket connection and authentication."""
    
    def test_connect_with_valid_token(self, socketio_client):
        """Test connecting with a valid JWT token."""
        assert socketio_client.is_connected()
        
        # Should receive connected event
        received = socketio_client.get_received()
        assert len(received) > 0
        
        connected_event = next((r for r in received if r['name'] == 'connected'), None)
        assert connected_event is not None
        assert connected_event['args'][0]['status'] == 'success'
    
    def test_connect_without_token(self):
        """Test connecting without authentication token."""
        client = socketio.test_client(
            app,
            flask_test_client=app.test_client()
        )
        
        # Connection should be rejected
        assert not client.is_connected()
    
    def test_connect_with_invalid_token(self):
        """Test connecting with an invalid token."""
        client = socketio.test_client(
            app,
            query_string='token=invalid_token',
            flask_test_client=app.test_client()
        )
        
        # Connection should be rejected
        assert not client.is_connected()
    
    def test_ping_pong(self, socketio_client):
        """Test ping/pong for connection keep-alive."""
        socketio_client.emit('ping')
        
        received = socketio_client.get_received()
        pong_event = next((r for r in received if r['name'] == 'pong'), None)
        
        assert pong_event is not None
        assert 'timestamp' in pong_event['args'][0]
    
    def test_disconnect(self, socketio_client):
        """Test disconnection."""
        assert socketio_client.is_connected()
        
        socketio_client.disconnect()
        
        assert not socketio_client.is_connected()


class TestMarketDataSubscription:
    """Test market data chart subscription and updates."""
    
    def test_subscribe_chart(self, socketio_client):
        """Test subscribing to chart data."""
        socketio_client.emit('subscribe_chart', {
            'symbol': 'RELIANCE',
            'timeframe': '5m'
        })
        
        received = socketio_client.get_received()
        subscribed_event = next((r for r in received if r['name'] == 'chart_subscribed'), None)
        
        assert subscribed_event is not None
        data = subscribed_event['args'][0]
        assert data['symbol'] == 'RELIANCE'
        assert data['timeframe'] == '5m'
        assert 'historical_candles' in data
        assert 'forming_candle' in data
    
    def test_subscribe_chart_missing_fields(self, socketio_client):
        """Test subscribing without required fields."""
        socketio_client.emit('subscribe_chart', {
            'symbol': 'RELIANCE'
            # Missing timeframe
        })
        
        received = socketio_client.get_received()
        error_event = next((r for r in received if r['name'] == 'error'), None)
        
        assert error_event is not None
        assert 'Missing required fields' in error_event['args'][0]['message']
    
    def test_unsubscribe_chart(self, socketio_client):
        """Test unsubscribing from chart data."""
        # First subscribe
        socketio_client.emit('subscribe_chart', {
            'symbol': 'RELIANCE',
            'timeframe': '5m'
        })
        socketio_client.get_received()  # Clear received events
        
        # Then unsubscribe
        socketio_client.emit('unsubscribe_chart', {
            'symbol': 'RELIANCE',
            'timeframe': '5m'
        })
        
        received = socketio_client.get_received()
        unsubscribed_event = next((r for r in received if r['name'] == 'chart_unsubscribed'), None)
        
        assert unsubscribed_event is not None
        data = unsubscribed_event['args'][0]
        assert data['symbol'] == 'RELIANCE'
        assert data['timeframe'] == '5m'


class TestTradingActivitySubscription:
    """Test trading activity subscription and updates."""
    
    def test_subscribe_account(self, socketio_client, test_account):
        """Test subscribing to account trading activity."""
        socketio_client.emit('subscribe_account', {
            'account_id': str(test_account.id),
            'trading_mode': 'paper'
        })
        
        received = socketio_client.get_received()
        subscribed_event = next((r for r in received if r['name'] == 'account_subscribed'), None)
        
        assert subscribed_event is not None
        data = subscribed_event['args'][0]
        assert data['account_id'] == str(test_account.id)
        assert data['trading_mode'] == 'paper'
        assert 'positions' in data
        assert 'orders' in data
        assert 'pnl_summary' in data
    
    def test_subscribe_account_missing_fields(self, socketio_client):
        """Test subscribing without required fields."""
        socketio_client.emit('subscribe_account', {
            'trading_mode': 'paper'
            # Missing account_id
        })
        
        received = socketio_client.get_received()
        error_event = next((r for r in received if r['name'] == 'error'), None)
        
        assert error_event is not None
        assert 'Missing required field' in error_event['args'][0]['message']
    
    def test_unsubscribe_account(self, socketio_client, test_account):
        """Test unsubscribing from account trading activity."""
        # First subscribe
        socketio_client.emit('subscribe_account', {
            'account_id': str(test_account.id),
            'trading_mode': 'paper'
        })
        socketio_client.get_received()  # Clear received events
        
        # Then unsubscribe
        socketio_client.emit('unsubscribe_account', {
            'account_id': str(test_account.id),
            'trading_mode': 'paper'
        })
        
        received = socketio_client.get_received()
        unsubscribed_event = next((r for r in received if r['name'] == 'account_unsubscribed'), None)
        
        assert unsubscribed_event is not None
        data = unsubscribed_event['args'][0]
        assert data['account_id'] == str(test_account.id)
        assert data['trading_mode'] == 'paper'


class TestNotificationSubscription:
    """Test notification subscription and updates."""
    
    def test_subscribe_notifications(self, socketio_client):
        """Test subscribing to notifications."""
        socketio_client.emit('subscribe_notifications')
        
        received = socketio_client.get_received()
        subscribed_event = next((r for r in received if r['name'] == 'notifications_subscribed'), None)
        
        assert subscribed_event is not None
        data = subscribed_event['args'][0]
        assert 'user_id' in data
        assert 'unread_notifications' in data
        assert 'unread_count' in data
    
    def test_unsubscribe_notifications(self, socketio_client):
        """Test unsubscribing from notifications."""
        # First subscribe
        socketio_client.emit('subscribe_notifications')
        socketio_client.get_received()  # Clear received events
        
        # Then unsubscribe
        socketio_client.emit('unsubscribe_notifications')
        
        received = socketio_client.get_received()
        unsubscribed_event = next((r for r in received if r['name'] == 'notifications_unsubscribed'), None)
        
        assert unsubscribed_event is not None
        assert 'user_id' in unsubscribed_event['args'][0]
    
    def test_mark_notification_read(self, socketio_client):
        """Test marking a notification as read."""
        notification_id = str(uuid.uuid4())
        
        socketio_client.emit('mark_notification_read', {
            'notification_id': notification_id
        })
        
        received = socketio_client.get_received()
        # May receive error if notification doesn't exist, which is expected
        assert len(received) > 0
    
    def test_mark_all_notifications_read(self, socketio_client):
        """Test marking all notifications as read."""
        socketio_client.emit('mark_all_notifications_read')
        
        received = socketio_client.get_received()
        read_event = next((r for r in received if r['name'] == 'all_notifications_read'), None)
        
        assert read_event is not None
        data = read_event['args'][0]
        assert 'count' in data
        assert 'read_at' in data


class TestRoomManager:
    """Test room naming and management utilities."""
    
    def test_get_chart_room(self):
        """Test chart room name generation."""
        room = RoomManager.get_chart_room('RELIANCE', '5m')
        assert room == 'chart:RELIANCE:5m'
    
    def test_get_account_room(self):
        """Test account room name generation."""
        account_id = str(uuid.uuid4())
        room = RoomManager.get_account_room(account_id, 'paper')
        assert room == f'account:{account_id}:paper'
    
    def test_get_user_room(self):
        """Test user room name generation."""
        user_id = str(uuid.uuid4())
        room = RoomManager.get_user_room(user_id)
        assert room == f'user:{user_id}'
    
    def test_get_strategy_room(self):
        """Test strategy room name generation."""
        strategy_id = str(uuid.uuid4())
        room = RoomManager.get_strategy_room(strategy_id)
        assert room == f'strategy:{strategy_id}'
    
    def test_get_position_room(self):
        """Test position room name generation."""
        account_id = str(uuid.uuid4())
        room = RoomManager.get_position_room(account_id, 'live')
        assert room == f'positions:{account_id}:live'
    
    def test_get_order_room(self):
        """Test order room name generation."""
        account_id = str(uuid.uuid4())
        room = RoomManager.get_order_room(account_id, 'paper')
        assert room == f'orders:{account_id}:paper'
    
    def test_parse_chart_room(self):
        """Test parsing chart room name."""
        symbol, timeframe = RoomManager.parse_chart_room('chart:RELIANCE:5m')
        assert symbol == 'RELIANCE'
        assert timeframe == '5m'
    
    def test_parse_account_room(self):
        """Test parsing account room name."""
        account_id = str(uuid.uuid4())
        parsed_id, mode = RoomManager.parse_account_room(f'account:{account_id}:paper')
        assert parsed_id == account_id
        assert mode == 'paper'
    
    def test_get_all_chart_rooms_for_symbol(self):
        """Test getting all chart rooms for a symbol."""
        timeframes = ['1m', '5m', '15m']
        rooms = RoomManager.get_all_chart_rooms_for_symbol('RELIANCE', timeframes)
        
        assert len(rooms) == 3
        assert 'chart:RELIANCE:1m' in rooms
        assert 'chart:RELIANCE:5m' in rooms
        assert 'chart:RELIANCE:15m' in rooms


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
