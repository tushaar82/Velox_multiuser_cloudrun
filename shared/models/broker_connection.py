"""Database models for broker connections."""

from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from shared.database.connection import Base


class BrokerConnection(Base):
    """Broker connection model."""
    
    __tablename__ = 'broker_connections'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey('user_accounts.id'), nullable=False)
    broker_name = Column(String(50), nullable=False)
    credentials_encrypted = Column(Text, nullable=False)
    is_connected = Column(Boolean, default=False)
    last_connected_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to user account
    # account = relationship("UserAccount", back_populates="broker_connections")
    
    def __repr__(self):
        return f"<BrokerConnection(id={self.id}, account_id={self.account_id}, broker={self.broker_name}, connected={self.is_connected})>"
