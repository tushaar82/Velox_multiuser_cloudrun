"""
Notification Service - Handles notification creation and delivery.
Implements multi-channel notification delivery (in-app, email, SMS).
"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from collections import defaultdict
import uuid

from sqlalchemy.orm import Session

try:
    from twilio.rest import Client as TwilioClient
    TWILIO_AVAILABLE = True
except ImportError:
    TwilioClient = None
    TWILIO_AVAILABLE = False

from shared.models.notification import (
    Notification, NotificationData, NotificationRequest,
    NotificationType, NotificationSeverity, NotificationChannel,
    NotificationPreferences, NotificationChannelConfig
)
from shared.database.connection import get_db_session
from shared.config import get_settings

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for creating and delivering notifications."""
    
    def __init__(self):
        self.settings = get_settings()
        self._notification_batch = defaultdict(list)
        self._last_batch_time = defaultdict(lambda: datetime.utcnow())
        self._batch_interval = timedelta(minutes=5)  # Batch notifications every 5 minutes
        
        # Initialize email client
        self._smtp_host = getattr(self.settings, 'smtp_host', 'smtp.gmail.com')
        self._smtp_port = getattr(self.settings, 'smtp_port', 587)
        self._smtp_user = getattr(self.settings, 'smtp_user', None)
        self._smtp_password = getattr(self.settings, 'smtp_password', None)
        self._from_email = getattr(self.settings, 'from_email', 'noreply@trading-platform.com')
        
        # Initialize Twilio client for SMS
        self._twilio_account_sid = getattr(self.settings, 'twilio_account_sid', None)
        self._twilio_auth_token = getattr(self.settings, 'twilio_auth_token', None)
        self._twilio_from_number = getattr(self.settings, 'twilio_from_number', None)
        
        if TWILIO_AVAILABLE and self._twilio_account_sid and self._twilio_auth_token:
            self._twilio_client = TwilioClient(
                self._twilio_account_sid,
                self._twilio_auth_token
            )
        else:
            self._twilio_client = None
            if not TWILIO_AVAILABLE:
                logger.warning("Twilio library not installed. SMS notifications will be disabled.")
            else:
                logger.warning("Twilio credentials not configured. SMS notifications will be disabled.")
    
    def create_notification(
        self,
        db: Session,
        request: NotificationRequest
    ) -> NotificationData:
        """
        Create a notification and deliver it through configured channels.
        
        Args:
            db: Database session
            request: Notification request
            
        Returns:
            Created notification data
        """
        # Create notification in database
        notification = Notification(
            id=uuid.uuid4(),
            user_id=uuid.UUID(request.user_id),
            type=request.type,
            title=request.title,
            message=request.message,
            severity=request.severity,
            created_at=datetime.utcnow()
        )
        
        db.add(notification)
        db.commit()
        db.refresh(notification)
        
        notification_data = NotificationData.from_orm(notification)
        
        # Determine delivery channels
        channels = request.channels
        if not channels:
            # Get user preferences
            preferences = self._get_user_preferences(db, request.user_id)
            channels = preferences.get_channels_for_type(request.type)
        
        # Deliver through channels based on severity
        self._deliver_notification(
            db=db,
            user_id=request.user_id,
            notification_data=notification_data,
            channels=channels,
            metadata=request.metadata
        )
        
        logger.info(
            f"Created notification {notification.id} for user {request.user_id}: "
            f"{request.type.value} - {request.severity.value}"
        )
        
        return notification_data
    
    def _deliver_notification(
        self,
        db: Session,
        user_id: str,
        notification_data: NotificationData,
        channels: List[NotificationChannel],
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Deliver notification through specified channels.
        
        Args:
            db: Database session
            user_id: User ID
            notification_data: Notification data
            channels: List of delivery channels
            metadata: Additional metadata
        """
        # Always deliver in-app notification via WebSocket (< 500ms latency)
        if NotificationChannel.IN_APP in channels or not channels:
            self._deliver_in_app(user_id, notification_data)
        
        # Check if we should batch this notification
        should_batch = self._should_batch_notification(notification_data.severity)
        
        if should_batch:
            # Add to batch
            self._add_to_batch(user_id, notification_data, channels, metadata)
        else:
            # Deliver immediately for high-priority notifications
            if NotificationChannel.EMAIL in channels:
                self._deliver_email(db, user_id, notification_data, metadata)
            
            if NotificationChannel.SMS in channels:
                self._deliver_sms(db, user_id, notification_data, metadata)
    
    def _should_batch_notification(self, severity: NotificationSeverity) -> bool:
        """
        Determine if notification should be batched to prevent spam.
        
        Args:
            severity: Notification severity
            
        Returns:
            True if should batch, False if should deliver immediately
        """
        # Don't batch critical or error notifications
        return severity in [NotificationSeverity.INFO, NotificationSeverity.WARNING]
    
    def _add_to_batch(
        self,
        user_id: str,
        notification_data: NotificationData,
        channels: List[NotificationChannel],
        metadata: Optional[Dict[str, Any]]
    ):
        """
        Add notification to batch for later delivery.
        
        Args:
            user_id: User ID
            notification_data: Notification data
            channels: Delivery channels
            metadata: Additional metadata
        """
        batch_key = f"{user_id}:{','.join(c.value for c in channels)}"
        self._notification_batch[batch_key].append({
            'notification': notification_data,
            'metadata': metadata
        })
        
        logger.debug(f"Added notification to batch for user {user_id}")
    
    def process_batches(self, db: Session):
        """
        Process batched notifications and deliver them.
        Should be called periodically (e.g., every 5 minutes).
        
        Args:
            db: Database session
        """
        current_time = datetime.utcnow()
        
        for batch_key, notifications in list(self._notification_batch.items()):
            if current_time - self._last_batch_time[batch_key] >= self._batch_interval:
                # Parse batch key
                user_id, channels_str = batch_key.split(':', 1)
                channels = [NotificationChannel(c) for c in channels_str.split(',')]
                
                # Deliver batched notifications
                if NotificationChannel.EMAIL in channels:
                    self._deliver_batched_email(db, user_id, notifications)
                
                if NotificationChannel.SMS in channels:
                    self._deliver_batched_sms(db, user_id, notifications)
                
                # Clear batch
                del self._notification_batch[batch_key]
                self._last_batch_time[batch_key] = current_time
                
                logger.info(f"Processed batch of {len(notifications)} notifications for user {user_id}")
    
    def _deliver_in_app(self, user_id: str, notification_data: NotificationData):
        """
        Deliver in-app notification via WebSocket.
        
        Args:
            user_id: User ID
            notification_data: Notification data
        """
        try:
            from websocket_service.notification_events import push_notification
            
            push_notification(user_id, notification_data)
            
            logger.debug(f"Delivered in-app notification to user {user_id}")
            
        except Exception as e:
            logger.error(f"Failed to deliver in-app notification: {e}")
    
    def _deliver_email(
        self,
        db: Session,
        user_id: str,
        notification_data: NotificationData,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Deliver email notification via SMTP.
        
        Args:
            db: Database session
            user_id: User ID
            notification_data: Notification data
            metadata: Additional metadata
        """
        if not self._smtp_user or not self._smtp_password:
            logger.warning("SMTP credentials not configured. Email notification skipped.")
            return
        
        try:
            # Get user email
            from shared.models import User
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.error(f"User {user_id} not found for email notification")
                return
            
            # Create email message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"[{notification_data.severity.value.upper()}] {notification_data.title}"
            msg['From'] = self._from_email
            msg['To'] = user.email
            
            # Create HTML body
            html_body = self._create_email_html(notification_data, metadata)
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send email
            with smtplib.SMTP(self._smtp_host, self._smtp_port) as server:
                server.starttls()
                server.login(self._smtp_user, self._smtp_password)
                server.send_message(msg)
            
            logger.info(f"Delivered email notification to {user.email}")
            
        except Exception as e:
            logger.error(f"Failed to deliver email notification: {e}")
    
    def _deliver_batched_email(
        self,
        db: Session,
        user_id: str,
        notifications: List[Dict[str, Any]]
    ):
        """
        Deliver batched email notifications.
        
        Args:
            db: Database session
            user_id: User ID
            notifications: List of notification dictionaries
        """
        if not self._smtp_user or not self._smtp_password:
            logger.warning("SMTP credentials not configured. Batched email skipped.")
            return
        
        try:
            # Get user email
            from shared.models import User
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                logger.error(f"User {user_id} not found for batched email")
                return
            
            # Create email message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"Trading Platform - {len(notifications)} New Notifications"
            msg['From'] = self._from_email
            msg['To'] = user.email
            
            # Create HTML body with all notifications
            html_body = self._create_batched_email_html(notifications)
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send email
            with smtplib.SMTP(self._smtp_host, self._smtp_port) as server:
                server.starttls()
                server.login(self._smtp_user, self._smtp_password)
                server.send_message(msg)
            
            logger.info(f"Delivered batched email with {len(notifications)} notifications to {user.email}")
            
        except Exception as e:
            logger.error(f"Failed to deliver batched email: {e}")
    
    def _deliver_sms(
        self,
        db: Session,
        user_id: str,
        notification_data: NotificationData,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Deliver SMS notification via Twilio.
        
        Args:
            db: Database session
            user_id: User ID
            notification_data: Notification data
            metadata: Additional metadata
        """
        if not self._twilio_client:
            logger.warning("Twilio not configured. SMS notification skipped.")
            return
        
        try:
            # Get user phone number
            from shared.models import User
            user = db.query(User).filter(User.id == user_id).first()
            if not user or not hasattr(user, 'phone_number') or not user.phone_number:
                logger.warning(f"User {user_id} has no phone number for SMS notification")
                return
            
            # Create SMS message (max 160 characters)
            sms_body = f"[{notification_data.severity.value.upper()}] {notification_data.title}: {notification_data.message[:100]}"
            
            # Send SMS
            message = self._twilio_client.messages.create(
                body=sms_body,
                from_=self._twilio_from_number,
                to=user.phone_number
            )
            
            logger.info(f"Delivered SMS notification to {user.phone_number}: {message.sid}")
            
        except Exception as e:
            logger.error(f"Failed to deliver SMS notification: {e}")
    
    def _deliver_batched_sms(
        self,
        db: Session,
        user_id: str,
        notifications: List[Dict[str, Any]]
    ):
        """
        Deliver batched SMS notifications.
        
        Args:
            db: Database session
            user_id: User ID
            notifications: List of notification dictionaries
        """
        if not self._twilio_client:
            logger.warning("Twilio not configured. Batched SMS skipped.")
            return
        
        try:
            # Get user phone number
            from shared.models import User
            user = db.query(User).filter(User.id == user_id).first()
            if not user or not hasattr(user, 'phone_number') or not user.phone_number:
                logger.warning(f"User {user_id} has no phone number for batched SMS")
                return
            
            # Create SMS message
            sms_body = f"You have {len(notifications)} new notifications. Check the app for details."
            
            # Send SMS
            message = self._twilio_client.messages.create(
                body=sms_body,
                from_=self._twilio_from_number,
                to=user.phone_number
            )
            
            logger.info(f"Delivered batched SMS to {user.phone_number}: {message.sid}")
            
        except Exception as e:
            logger.error(f"Failed to deliver batched SMS: {e}")
    
    def _create_email_html(
        self,
        notification_data: NotificationData,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create HTML email body for a notification.
        
        Args:
            notification_data: Notification data
            metadata: Additional metadata
            
        Returns:
            HTML string
        """
        severity_colors = {
            NotificationSeverity.INFO: '#2196F3',
            NotificationSeverity.WARNING: '#FF9800',
            NotificationSeverity.ERROR: '#F44336',
            NotificationSeverity.CRITICAL: '#D32F2F'
        }
        
        color = severity_colors.get(notification_data.severity, '#2196F3')
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <div style="border-left: 4px solid {color}; padding-left: 15px;">
                <h2 style="color: {color}; margin: 0;">{notification_data.title}</h2>
                <p style="color: #666; margin: 5px 0;">{notification_data.created_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p style="margin: 15px 0;">{notification_data.message}</p>
            </div>
            <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
            <p style="color: #999; font-size: 12px;">
                This is an automated notification from your Trading Platform.
            </p>
        </body>
        </html>
        """
        
        return html
    
    def _create_batched_email_html(self, notifications: List[Dict[str, Any]]) -> str:
        """
        Create HTML email body for batched notifications.
        
        Args:
            notifications: List of notification dictionaries
            
        Returns:
            HTML string
        """
        severity_colors = {
            NotificationSeverity.INFO: '#2196F3',
            NotificationSeverity.WARNING: '#FF9800',
            NotificationSeverity.ERROR: '#F44336',
            NotificationSeverity.CRITICAL: '#D32F2F'
        }
        
        notifications_html = ""
        for item in notifications:
            notification = item['notification']
            color = severity_colors.get(notification.severity, '#2196F3')
            
            notifications_html += f"""
            <div style="border-left: 4px solid {color}; padding-left: 15px; margin-bottom: 20px;">
                <h3 style="color: {color}; margin: 0;">{notification.title}</h3>
                <p style="color: #666; margin: 5px 0;">{notification.created_at.strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p style="margin: 10px 0;">{notification.message}</p>
            </div>
            """
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h1>Trading Platform Notifications</h1>
            <p>You have {len(notifications)} new notifications:</p>
            {notifications_html}
            <hr style="border: none; border-top: 1px solid #ddd; margin: 20px 0;">
            <p style="color: #999; font-size: 12px;">
                This is an automated notification from your Trading Platform.
            </p>
        </body>
        </html>
        """
        
        return html
    
    def _get_user_preferences(
        self,
        db: Session,
        user_id: str
    ) -> NotificationPreferences:
        """
        Get user notification preferences.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Notification preferences
        """
        # TODO: Implement user preferences storage and retrieval
        # For now, return default preferences
        default_preferences = {
            NotificationType.ORDER_EXECUTED.value: NotificationChannelConfig(
                enabled=True,
                channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL]
            ),
            NotificationType.STRATEGY_ERROR.value: NotificationChannelConfig(
                enabled=True,
                channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL, NotificationChannel.SMS]
            ),
            NotificationType.THRESHOLD_ALERT.value: NotificationChannelConfig(
                enabled=True,
                channels=[NotificationChannel.IN_APP, NotificationChannel.SMS]
            ),
            NotificationType.CONNECTION_LOST.value: NotificationChannelConfig(
                enabled=True,
                channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL]
            ),
            NotificationType.SYSTEM_ALERT.value: NotificationChannelConfig(
                enabled=True,
                channels=[NotificationChannel.IN_APP]
            ),
            NotificationType.TRAILING_STOP_TRIGGERED.value: NotificationChannelConfig(
                enabled=True,
                channels=[NotificationChannel.IN_APP, NotificationChannel.SMS]
            ),
            NotificationType.INVESTOR_INVITATION.value: NotificationChannelConfig(
                enabled=True,
                channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL]
            ),
            NotificationType.ACCOUNT_ACCESS_GRANTED.value: NotificationChannelConfig(
                enabled=True,
                channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL]
            ),
            NotificationType.SESSION_TIMEOUT_WARNING.value: NotificationChannelConfig(
                enabled=True,
                channels=[NotificationChannel.IN_APP]
            ),
            NotificationType.ACCOUNT_LOCKED.value: NotificationChannelConfig(
                enabled=True,
                channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL]
            ),
            NotificationType.LOSS_LIMIT_BREACHED.value: NotificationChannelConfig(
                enabled=True,
                channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL, NotificationChannel.SMS]
            ),
            NotificationType.STRATEGY_PAUSED.value: NotificationChannelConfig(
                enabled=True,
                channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL]
            ),
        }
        
        return NotificationPreferences(
            user_id=user_id,
            preferences=default_preferences
        )
    
    def get_notification_history(
        self,
        db: Session,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        unread_only: bool = False
    ) -> List[NotificationData]:
        """
        Get notification history for a user.
        
        Args:
            db: Database session
            user_id: User ID
            limit: Maximum number of notifications to return
            offset: Offset for pagination
            unread_only: If True, return only unread notifications
            
        Returns:
            List of notification data
        """
        query = db.query(Notification).filter(Notification.user_id == user_id)
        
        if unread_only:
            query = query.filter(Notification.read_at.is_(None))
        
        notifications = query.order_by(
            Notification.created_at.desc()
        ).limit(limit).offset(offset).all()
        
        return [NotificationData.from_orm(n) for n in notifications]
    
    def mark_as_read(
        self,
        db: Session,
        user_id: str,
        notification_id: str
    ) -> bool:
        """
        Mark a notification as read.
        
        Args:
            db: Database session
            user_id: User ID
            notification_id: Notification ID
            
        Returns:
            True if successful, False otherwise
        """
        notification = db.query(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user_id
        ).first()
        
        if notification and not notification.read_at:
            notification.read_at = datetime.utcnow()
            db.commit()
            return True
        
        return False
    
    def mark_all_as_read(
        self,
        db: Session,
        user_id: str
    ) -> int:
        """
        Mark all notifications as read for a user.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Number of notifications marked as read
        """
        count = db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.read_at.is_(None)
        ).update({'read_at': datetime.utcnow()})
        
        db.commit()
        return count
    
    def get_unread_count(
        self,
        db: Session,
        user_id: str
    ) -> int:
        """
        Get count of unread notifications for a user.
        
        Args:
            db: Database session
            user_id: User ID
            
        Returns:
            Number of unread notifications
        """
        return db.query(Notification).filter(
            Notification.user_id == user_id,
            Notification.read_at.is_(None)
        ).count()


# Global notification service instance
_notification_service = None


def get_notification_service() -> NotificationService:
    """Get or create the global notification service instance."""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service
