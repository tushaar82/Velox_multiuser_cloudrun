"""Broker connection service for managing broker integrations."""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.orm import Session

from shared.models.broker_connection import BrokerConnection
from shared.brokers.base import IBrokerConnector, BrokerCredentials
from shared.brokers.angel_one_connector import AngelOneConnector
from shared.brokers.mock_connector import MockBrokerConnector
from shared.utils.encryption import CredentialEncryption

logger = logging.getLogger(__name__)


class BrokerService:
    """Service for managing broker connections."""
    
    # Available broker plugins
    BROKER_PLUGINS = {
        'angel_one': {
            'name': 'Angel One SmartAPI',
            'connector_class': AngelOneConnector,
            'description': 'Angel One SmartAPI integration for NSE, BSE, NFO, MCX',
            'credentials_required': ['api_key', 'client_code', 'password', 'totp_token']
        },
        'mock': {
            'name': 'Mock Broker',
            'connector_class': MockBrokerConnector,
            'description': 'Mock broker for offline testing and development',
            'credentials_required': []
        }
    }
    
    def __init__(self, db_session: Session, encryption_key: Optional[str] = None):
        """
        Initialize broker service.
        
        Args:
            db_session: Database session
            encryption_key: Encryption key for credentials
        """
        self.db = db_session
        self.encryption = CredentialEncryption(encryption_key)
        self._active_connectors: Dict[str, IBrokerConnector] = {}
    
    def connect_broker(
        self,
        account_id: str,
        broker_name: str,
        credentials: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Connect a broker account.
        
        Args:
            account_id: User account ID
            broker_name: Name of broker plugin
            credentials: Broker credentials dictionary
            
        Returns:
            Connection status dictionary
            
        Raises:
            ValueError: If broker not supported or credentials invalid
            ConnectionError: If connection fails
        """
        # Validate broker
        if broker_name not in self.BROKER_PLUGINS:
            raise ValueError(f"Unsupported broker: {broker_name}")
        
        plugin = self.BROKER_PLUGINS[broker_name]
        
        # Validate required credentials
        required = plugin['credentials_required']
        missing = [field for field in required if field not in credentials]
        if missing:
            raise ValueError(f"Missing required credentials: {', '.join(missing)}")
        
        try:
            # Create broker connector
            connector_class = plugin['connector_class']
            connector = connector_class()
            
            # Prepare credentials
            broker_creds = BrokerCredentials(
                api_key=credentials.get('api_key', ''),
                api_secret=credentials.get('password', ''),
                user_id=credentials.get('client_code'),
                additional_params={
                    k: v for k, v in credentials.items()
                    if k not in ['api_key', 'password', 'client_code']
                }
            )
            
            # Attempt connection
            connector.connect(broker_creds)
            
            # Encrypt and store credentials
            encrypted_creds = self.encryption.encrypt_dict(credentials)
            
            # Check if connection already exists
            existing = self.db.query(BrokerConnection).filter_by(
                account_id=account_id,
                broker_name=broker_name
            ).first()
            
            if existing:
                # Update existing connection
                existing.credentials_encrypted = encrypted_creds
                existing.is_connected = True
                existing.last_connected_at = datetime.utcnow()
                connection = existing
            else:
                # Create new connection
                connection = BrokerConnection(
                    account_id=account_id,
                    broker_name=broker_name,
                    credentials_encrypted=encrypted_creds,
                    is_connected=True,
                    last_connected_at=datetime.utcnow()
                )
                self.db.add(connection)
            
            self.db.commit()
            
            # Store active connector
            connector_key = f"{account_id}_{broker_name}"
            self._active_connectors[connector_key] = connector
            
            logger.info(f"Broker connected: {broker_name} for account {account_id}")
            
            return {
                'connection_id': str(connection.id),
                'broker_name': broker_name,
                'status': 'connected',
                'connected_at': connection.last_connected_at.isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to connect broker {broker_name}: {str(e)}")
            self.db.rollback()
            raise ConnectionError(f"Broker connection failed: {str(e)}")
    
    def disconnect_broker(self, account_id: str, broker_name: str) -> Dict[str, Any]:
        """
        Disconnect a broker account.
        
        Args:
            account_id: User account ID
            broker_name: Name of broker plugin
            
        Returns:
            Disconnection status dictionary
        """
        try:
            # Get connection from database
            connection = self.db.query(BrokerConnection).filter_by(
                account_id=account_id,
                broker_name=broker_name
            ).first()
            
            if not connection:
                raise ValueError(f"No connection found for {broker_name}")
            
            # Disconnect active connector if exists
            connector_key = f"{account_id}_{broker_name}"
            if connector_key in self._active_connectors:
                connector = self._active_connectors[connector_key]
                connector.disconnect()
                del self._active_connectors[connector_key]
            
            # Update database
            connection.is_connected = False
            self.db.commit()
            
            logger.info(f"Broker disconnected: {broker_name} for account {account_id}")
            
            return {
                'broker_name': broker_name,
                'status': 'disconnected'
            }
            
        except Exception as e:
            logger.error(f"Failed to disconnect broker {broker_name}: {str(e)}")
            self.db.rollback()
            raise
    
    def get_connection_status(self, account_id: str, broker_name: str) -> Dict[str, Any]:
        """
        Get broker connection status.
        
        Args:
            account_id: User account ID
            broker_name: Name of broker plugin
            
        Returns:
            Connection status dictionary
        """
        connection = self.db.query(BrokerConnection).filter_by(
            account_id=account_id,
            broker_name=broker_name
        ).first()
        
        if not connection:
            return {
                'broker_name': broker_name,
                'status': 'not_connected',
                'connected': False
            }
        
        # Check if connector is active
        connector_key = f"{account_id}_{broker_name}"
        is_active = connector_key in self._active_connectors
        
        if is_active:
            connector = self._active_connectors[connector_key]
            is_connected = connector.is_connected()
        else:
            is_connected = False
        
        return {
            'connection_id': str(connection.id),
            'broker_name': broker_name,
            'status': 'connected' if is_connected else 'disconnected',
            'connected': is_connected,
            'last_connected_at': connection.last_connected_at.isoformat() if connection.last_connected_at else None
        }
    
    def list_available_brokers(self) -> List[Dict[str, Any]]:
        """
        List all available broker plugins.
        
        Returns:
            List of broker plugin information
        """
        brokers = []
        for broker_id, plugin in self.BROKER_PLUGINS.items():
            brokers.append({
                'id': broker_id,
                'name': plugin['name'],
                'description': plugin['description'],
                'credentials_required': plugin['credentials_required']
            })
        return brokers
    
    def get_connector(self, account_id: str, broker_name: str) -> Optional[IBrokerConnector]:
        """
        Get active broker connector.
        
        Args:
            account_id: User account ID
            broker_name: Name of broker plugin
            
        Returns:
            Broker connector instance or None
        """
        connector_key = f"{account_id}_{broker_name}"
        return self._active_connectors.get(connector_key)
    
    def reconnect_broker(self, account_id: str, broker_name: str) -> Dict[str, Any]:
        """
        Reconnect a previously connected broker.
        
        Args:
            account_id: User account ID
            broker_name: Name of broker plugin
            
        Returns:
            Connection status dictionary
        """
        # Get stored connection
        connection = self.db.query(BrokerConnection).filter_by(
            account_id=account_id,
            broker_name=broker_name
        ).first()
        
        if not connection:
            raise ValueError(f"No stored connection found for {broker_name}")
        
        # Decrypt credentials
        credentials = self.encryption.decrypt_dict(connection.credentials_encrypted)
        
        # Reconnect
        return self.connect_broker(account_id, broker_name, credentials)
