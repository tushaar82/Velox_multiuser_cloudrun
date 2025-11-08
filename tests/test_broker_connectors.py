"""Unit tests for broker connectors."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from shared.brokers.base import (
    BrokerCredentials,
    BrokerOrder,
    BrokerOrderResponse,
    BrokerPosition,
    AccountInfo
)
from shared.brokers.mock_connector import MockBrokerConnector
from shared.utils.encryption import CredentialEncryption


class TestMockBrokerConnector:
    """Tests for mock broker connector."""
    
    def test_connection_with_valid_credentials(self):
        """Test broker connection with valid credentials."""
        connector = MockBrokerConnector()
        credentials = BrokerCredentials(
            api_key='test_key',
            api_secret='test_secret'
        )
        
        # Should not raise exception
        connector.connect(credentials)
        assert connector.is_connected()
    
    def test_connection_status(self):
        """Test connection status check."""
        connector = MockBrokerConnector()
        
        # Initially not connected
        assert not connector.is_connected()
        
        # Connect
        credentials = BrokerCredentials(api_key='test', api_secret='test')
        connector.connect(credentials)
        assert connector.is_connected()
        
        # Disconnect
        connector.disconnect()
        assert not connector.is_connected()
    
    def test_order_placement(self):
        """Test order placement and status retrieval."""
        connector = MockBrokerConnector()
        credentials = BrokerCredentials(api_key='test', api_secret='test')
        connector.connect(credentials)
        
        # Place market order
        order = BrokerOrder(
            symbol='RELIANCE',
            side='buy',
            quantity=10,
            order_type='market',
            exchange='NSE'
        )
        
        response = connector.place_order(order)
        
        assert response.broker_order_id is not None
        assert response.status == 'filled'
        
        # Check order status
        status = connector.get_order_status(response.broker_order_id)
        assert status == 'filled'
    
    def test_order_placement_without_connection(self):
        """Test order placement fails when not connected."""
        connector = MockBrokerConnector()
        
        order = BrokerOrder(
            symbol='RELIANCE',
            side='buy',
            quantity=10,
            order_type='market'
        )
        
        with pytest.raises(ConnectionError):
            connector.place_order(order)
    
    def test_position_tracking(self):
        """Test position tracking after order fills."""
        connector = MockBrokerConnector()
        credentials = BrokerCredentials(api_key='test', api_secret='test')
        connector.connect(credentials)
        
        # Place buy order
        order = BrokerOrder(
            symbol='RELIANCE',
            side='buy',
            quantity=10,
            order_type='market',
            price=2450.0,
            exchange='NSE'
        )
        connector.place_order(order)
        
        # Check positions
        positions = connector.get_positions()
        assert len(positions) == 1
        assert positions[0].symbol == 'RELIANCE'
        assert positions[0].quantity == 10
    
    def test_order_cancellation(self):
        """Test order cancellation."""
        connector = MockBrokerConnector()
        credentials = BrokerCredentials(api_key='test', api_secret='test')
        connector.connect(credentials)
        
        # Mock orders are instantly filled, so we can't cancel them
        # This tests the error case
        order = BrokerOrder(
            symbol='RELIANCE',
            side='buy',
            quantity=10,
            order_type='market'
        )
        response = connector.place_order(order)
        
        # Try to cancel filled order
        with pytest.raises(ValueError, match="Cannot cancel filled order"):
            connector.cancel_order(response.broker_order_id)
    
    def test_account_info(self):
        """Test account information retrieval."""
        connector = MockBrokerConnector()
        credentials = BrokerCredentials(api_key='test', api_secret='test')
        connector.connect(credentials)
        
        account_info = connector.get_account_info()
        
        assert account_info.account_id == 'mock_account'
        assert account_info.available_funds > 0
        assert account_info.total_margin > 0
    
    def test_connection_lost_callback(self):
        """Test connection lost callback."""
        connector = MockBrokerConnector()
        credentials = BrokerCredentials(api_key='test', api_secret='test')
        connector.connect(credentials)
        
        callback_called = False
        
        def on_connection_lost():
            nonlocal callback_called
            callback_called = True
        
        connector.on_connection_lost(on_connection_lost)
        connector.simulate_connection_loss()
        
        assert callback_called
        assert not connector.is_connected()


class TestCredentialEncryption:
    """Tests for credential encryption utilities."""
    
    def test_key_generation(self):
        """Test encryption key generation."""
        key = CredentialEncryption.generate_key()
        assert key is not None
        assert len(key) > 0
    
    def test_encryption_decryption(self):
        """Test credential encryption and decryption."""
        key = CredentialEncryption.generate_key()
        encryption = CredentialEncryption(key)
        
        plaintext = "test_secret_password"
        encrypted = encryption.encrypt(plaintext)
        decrypted = encryption.decrypt(encrypted)
        
        assert encrypted != plaintext
        assert decrypted == plaintext
    
    def test_dict_encryption_decryption(self):
        """Test dictionary encryption and decryption."""
        key = CredentialEncryption.generate_key()
        encryption = CredentialEncryption(key)
        
        credentials = {
            'api_key': 'test_key',
            'api_secret': 'test_secret',
            'client_code': 'ABC123'
        }
        
        encrypted = encryption.encrypt_dict(credentials)
        decrypted = encryption.decrypt_dict(encrypted)
        
        assert decrypted == credentials
    
    def test_decryption_with_wrong_key(self):
        """Test decryption fails with wrong key."""
        key1 = CredentialEncryption.generate_key()
        key2 = CredentialEncryption.generate_key()
        
        encryption1 = CredentialEncryption(key1)
        encryption2 = CredentialEncryption(key2)
        
        plaintext = "test_secret"
        encrypted = encryption1.encrypt(plaintext)
        
        with pytest.raises(ValueError):
            encryption2.decrypt(encrypted)
    
    def test_key_derivation_from_password(self):
        """Test key derivation from password."""
        password = "my_secure_password"
        key1, salt = CredentialEncryption.derive_key_from_password(password)
        
        # Same password and salt should produce same key
        key2, _ = CredentialEncryption.derive_key_from_password(password, salt)
        assert key1 == key2
        
        # Different password should produce different key
        key3, _ = CredentialEncryption.derive_key_from_password("different_password", salt)
        assert key1 != key3


class TestAngelOneConnector:
    """Tests for Angel One connector (mocked)."""
    
    @pytest.mark.skipif(True, reason="SmartAPI not installed in test environment")
    @patch('shared.brokers.angel_one_connector.SmartConnect')
    def test_connection_with_valid_credentials(self, mock_smart_connect):
        """Test Angel One connection with valid credentials."""
        from shared.brokers.angel_one_connector import AngelOneConnector
        
        # Mock SmartConnect
        mock_api = MagicMock()
        mock_api.generateSession.return_value = {
            'status': True,
            'data': {
                'jwtToken': 'test_jwt',
                'refreshToken': 'test_refresh'
            }
        }
        mock_api.getfeedToken.return_value = 'test_feed_token'
        mock_smart_connect.return_value = mock_api
        
        connector = AngelOneConnector()
        credentials = BrokerCredentials(
            api_key='test_key',
            api_secret='test_password',
            user_id='ABC123',
            additional_params={'totp_token': 'JBSWY3DPEHPK3PXP'}
        )
        
        connector.connect(credentials)
        assert connector.is_connected()
    
    @pytest.mark.skipif(True, reason="SmartAPI not installed in test environment")
    @patch('shared.brokers.angel_one_connector.SmartConnect')
    def test_connection_with_invalid_credentials(self, mock_smart_connect):
        """Test Angel One connection fails with invalid credentials."""
        from shared.brokers.angel_one_connector import AngelOneConnector
        
        # Mock failed connection
        mock_api = MagicMock()
        mock_api.generateSession.return_value = None
        mock_smart_connect.return_value = mock_api
        
        connector = AngelOneConnector()
        credentials = BrokerCredentials(
            api_key='invalid_key',
            api_secret='invalid_password',
            user_id='ABC123',
            additional_params={'totp_token': 'JBSWY3DPEHPK3PXP'}
        )
        
        with pytest.raises(ConnectionError):
            connector.connect(credentials)
    
    @pytest.mark.skipif(True, reason="SmartAPI not installed in test environment")
    @patch('shared.brokers.angel_one_connector.SmartConnect')
    def test_order_placement(self, mock_smart_connect):
        """Test order placement with Angel One."""
        from shared.brokers.angel_one_connector import AngelOneConnector
        
        # Mock SmartConnect
        mock_api = MagicMock()
        mock_api.generateSession.return_value = {
            'status': True,
            'data': {
                'jwtToken': 'test_jwt',
                'refreshToken': 'test_refresh'
            }
        }
        mock_api.getfeedToken.return_value = 'test_feed_token'
        mock_api.placeOrder.return_value = {
            'status': True,
            'data': {'orderid': '123456'},
            'message': 'Order placed successfully'
        }
        mock_smart_connect.return_value = mock_api
        
        connector = AngelOneConnector()
        credentials = BrokerCredentials(
            api_key='test_key',
            api_secret='test_password',
            user_id='ABC123',
            additional_params={'totp_token': 'JBSWY3DPEHPK3PXP'}
        )
        connector.connect(credentials)
        
        order = BrokerOrder(
            symbol='RELIANCE',
            side='buy',
            quantity=10,
            order_type='market',
            exchange='NSE'
        )
        
        response = connector.place_order(order)
        assert response.broker_order_id == '123456'
        assert response.status == 'submitted'
    
    @pytest.mark.skipif(True, reason="SmartAPI not installed in test environment")
    @patch('shared.brokers.angel_one_connector.SmartConnect')
    def test_get_positions(self, mock_smart_connect):
        """Test getting positions from Angel One."""
        from shared.brokers.angel_one_connector import AngelOneConnector
        
        # Mock SmartConnect
        mock_api = MagicMock()
        mock_api.generateSession.return_value = {
            'status': True,
            'data': {
                'jwtToken': 'test_jwt',
                'refreshToken': 'test_refresh'
            }
        }
        mock_api.getfeedToken.return_value = 'test_feed_token'
        mock_api.position.return_value = {
            'status': True,
            'data': [
                {
                    'tradingsymbol': 'RELIANCE',
                    'exchange': 'NSE',
                    'netqty': 10,
                    'netprice': 2450.0,
                    'ltp': 2460.0,
                    'pnl': 100.0,
                    'producttype': 'INTRADAY'
                }
            ]
        }
        mock_smart_connect.return_value = mock_api
        
        connector = AngelOneConnector()
        credentials = BrokerCredentials(
            api_key='test_key',
            api_secret='test_password',
            user_id='ABC123',
            additional_params={'totp_token': 'JBSWY3DPEHPK3PXP'}
        )
        connector.connect(credentials)
        
        positions = connector.get_positions()
        assert len(positions) == 1
        assert positions[0].symbol == 'RELIANCE'
        assert positions[0].quantity == 10
