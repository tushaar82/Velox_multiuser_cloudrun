"""
Notification data models for notification service.
Implements Notification table and related data classes.
"""
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, ForeignKey, 
    String, Text, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from shared.database.connection import Base


class NotificationType(PyEnum):
    """Notification type enumeration."""
    ORDER_EXECUTED = "order_executed"
    STRATEGY_ERROR = "strategy_error"
    THRESHOLD_ALERT = "threshold_alert"
    CONNECTION_LOST = "connection_lost"
    SYSTEM_ALERT = "system_alert"
    TRAILING_STOP_TRIGGERED = "trailing_stop_triggered"
    INVESTOR_INVITATION = "investor_invitation"
    ACCOUNT_ACCESS_GRANTED = "account_access_granted"
    SESSION_TIMEOUT_WARNING = "session_timeout_warning"
    ACCOUNT_LOCKED = "account_locked"
    LOSS_LIMIT_BREACHED = "loss_limit_breached"
    STRATEGY_PAUSED = "strategy_paused"


class NotificationSeverity(PyEnum):
    """Notification severity enumeration."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class NotificationChannel(PyEnum):
    """Notification delivery channel enumeration."""
    IN_APP = "in_app"
    EMAIL = "email"
    SMS = "sms"


class Notification(Base):
    """Notification model for storing user notifications."""
    
    __tablename__ = "notifications"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    type = Column(
        Enum(NotificationType, name="notification_type", create_type=True),
        nullable=False
    )
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    severity = Column(
        Enum(NotificationSeverity, name="notification_severity", create_type=True),
        nullable=False,
        default=NotificationSeverity.INFO
    )
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", backref="notifications")
    
    __table_args__ = (
        Index("idx_notifications_user", "user_id", "created_at"),
        Index("idx_notifications_unread", "user_id", "read_at"),
    )
    
    def __repr__(self) -> str:
        return f"<Notification(id={self.id}, user_id={self.user_id}, type={self.type.value}, severity={self.severity.value})>"


@dataclass
class NotificationData:
    """Data class for notification information."""
    id: str
    user_id: str
    type: NotificationType
    title: str
    message: str
    severity: NotificationSeverity
    read_at: Optional[datetime]
    created_at: datetime
    
    @classmethod
    def from_orm(cls, notification: Notification) -> 'NotificationData':
        """Create NotificationData from SQLAlchemy Notification model."""
        return cls(
            id=str(notification.id),
            user_id=str(notification.user_id),
            type=notification.type,
            title=notification.title,
            message=notification.message,
            severity=notification.severity,
            read_at=notification.read_at,
            created_at=notification.created_at
        )


@dataclass
class NotificationChannelConfig:
    """Configuration for notification delivery channels."""
    enabled: bool
    channels: List[NotificationChannel]


@dataclass
class NotificationPreferences:
    """User notification preferences."""
    user_id: str
    preferences: Dict[str, NotificationChannelConfig]
    
    def get_channels_for_type(self, notification_type: NotificationType) -> List[NotificationChannel]:
        """Get enabled channels for a specific notification type."""
        config = self.preferences.get(notification_type.value)
        if config and config.enabled:
            return config.channels
        return []


@dataclass
class NotificationRequest:
    """Request to send a notification."""
    user_id: str
    type: NotificationType
    title: str
    message: str
    severity: NotificationSeverity
    channels: Optional[List[NotificationChannel]] = None
    metadata: Optional[Dict[str, Any]] = None
