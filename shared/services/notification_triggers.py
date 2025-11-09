"""
Notification Triggers - Implements notification triggers for various trading events.
"""
import logging
from typing import Optional, Dict, Any
from datetime import datetime

from sqlalchemy.orm import Session

from shared.models.notification import (
    NotificationRequest, NotificationType, NotificationSeverity, NotificationChannel
)
from shared.services.notification_service import get_notification_service

logger = logging.getLogger(__name__)


class NotificationTriggers:
    """Handles triggering notifications for various trading events."""
    
    def __init__(self):
        self.notification_service = get_notification_service()
    
    def trigger_order_executed(
        self,
        db: Session,
        user_id: str,
        order_id: str,
        symbol: str,
        side: str,
        quantity: int,
        price: float,
        trading_mode: str
    ):
        """
        Trigger notification when an order is executed.
        
        Args:
            db: Database session
            user_id: User ID
            order_id: Order ID
            symbol: Symbol
            side: Order side (buy/sell)
            quantity: Quantity
            price: Execution price
            trading_mode: Trading mode (paper/live)
        """
        mode_label = "Paper" if trading_mode == "paper" else "Live"
        
        request = NotificationRequest(
            user_id=user_id,
            type=NotificationType.ORDER_EXECUTED,
            title=f"{mode_label} Order Executed",
            message=f"Your {side.upper()} order for {quantity} shares of {symbol} was executed at ₹{price:.2f}",
            severity=NotificationSeverity.INFO,
            channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL],
            metadata={
                'order_id': order_id,
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'price': price,
                'trading_mode': trading_mode
            }
        )
        
        self.notification_service.create_notification(db, request)
        logger.info(f"Triggered order executed notification for user {user_id}")
    
    def trigger_strategy_error(
        self,
        db: Session,
        user_id: str,
        strategy_id: str,
        strategy_name: str,
        error_message: str,
        error_details: Optional[str] = None
    ):
        """
        Trigger notification when a strategy generates an error.
        
        Args:
            db: Database session
            user_id: User ID
            strategy_id: Strategy ID
            strategy_name: Strategy name
            error_message: Error message
            error_details: Detailed error information
        """
        message = f"Strategy '{strategy_name}' encountered an error: {error_message}"
        if error_details:
            message += f"\n\nDetails: {error_details}"
        
        request = NotificationRequest(
            user_id=user_id,
            type=NotificationType.STRATEGY_ERROR,
            title="Strategy Error",
            message=message,
            severity=NotificationSeverity.ERROR,
            channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL, NotificationChannel.SMS],
            metadata={
                'strategy_id': strategy_id,
                'strategy_name': strategy_name,
                'error_message': error_message,
                'error_details': error_details
            }
        )
        
        self.notification_service.create_notification(db, request)
        logger.info(f"Triggered strategy error notification for user {user_id}")
    
    def trigger_threshold_alert(
        self,
        db: Session,
        user_id: str,
        alert_type: str,
        symbol: str,
        current_value: float,
        threshold_value: float,
        trading_mode: str
    ):
        """
        Trigger notification when a position reaches a profit or loss threshold.
        
        Args:
            db: Database session
            user_id: User ID
            alert_type: Type of alert (profit/loss)
            symbol: Symbol
            current_value: Current P&L value
            threshold_value: Threshold value
            trading_mode: Trading mode (paper/live)
        """
        mode_label = "Paper" if trading_mode == "paper" else "Live"
        
        if alert_type == "profit":
            title = f"{mode_label} Profit Threshold Reached"
            message = f"Your position in {symbol} has reached a profit of ₹{current_value:.2f} (threshold: ₹{threshold_value:.2f})"
            severity = NotificationSeverity.INFO
        else:
            title = f"{mode_label} Loss Threshold Reached"
            message = f"Your position in {symbol} has reached a loss of ₹{abs(current_value):.2f} (threshold: ₹{abs(threshold_value):.2f})"
            severity = NotificationSeverity.WARNING
        
        request = NotificationRequest(
            user_id=user_id,
            type=NotificationType.THRESHOLD_ALERT,
            title=title,
            message=message,
            severity=severity,
            channels=[NotificationChannel.IN_APP, NotificationChannel.SMS],
            metadata={
                'alert_type': alert_type,
                'symbol': symbol,
                'current_value': current_value,
                'threshold_value': threshold_value,
                'trading_mode': trading_mode
            }
        )
        
        self.notification_service.create_notification(db, request)
        logger.info(f"Triggered threshold alert notification for user {user_id}")
    
    def trigger_connection_lost(
        self,
        db: Session,
        user_id: str,
        connection_type: str,
        connection_name: str,
        error_message: Optional[str] = None
    ):
        """
        Trigger notification when broker or market data connection is lost.
        
        Args:
            db: Database session
            user_id: User ID
            connection_type: Type of connection (broker/market_data)
            connection_name: Name of the connection
            error_message: Optional error message
        """
        if connection_type == "broker":
            title = "Broker Connection Lost"
            message = f"Connection to broker '{connection_name}' has been lost. Attempting to reconnect..."
        else:
            title = "Market Data Connection Lost"
            message = f"Market data feed '{connection_name}' connection has been lost. Attempting to reconnect..."
        
        if error_message:
            message += f"\n\nError: {error_message}"
        
        request = NotificationRequest(
            user_id=user_id,
            type=NotificationType.CONNECTION_LOST,
            title=title,
            message=message,
            severity=NotificationSeverity.ERROR,
            channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL],
            metadata={
                'connection_type': connection_type,
                'connection_name': connection_name,
                'error_message': error_message
            }
        )
        
        self.notification_service.create_notification(db, request)
        logger.info(f"Triggered connection lost notification for user {user_id}")
    
    def trigger_trailing_stop_triggered(
        self,
        db: Session,
        user_id: str,
        position_id: str,
        symbol: str,
        side: str,
        stop_price: float,
        current_price: float,
        trading_mode: str
    ):
        """
        Trigger notification when trailing stop-loss is triggered.
        
        Args:
            db: Database session
            user_id: User ID
            position_id: Position ID
            symbol: Symbol
            side: Position side (long/short)
            stop_price: Stop price
            current_price: Current price
            trading_mode: Trading mode (paper/live)
        """
        mode_label = "Paper" if trading_mode == "paper" else "Live"
        
        request = NotificationRequest(
            user_id=user_id,
            type=NotificationType.TRAILING_STOP_TRIGGERED,
            title=f"{mode_label} Trailing Stop Triggered",
            message=f"Trailing stop-loss triggered for {side.upper()} position in {symbol}. Stop price: ₹{stop_price:.2f}, Current price: ₹{current_price:.2f}",
            severity=NotificationSeverity.WARNING,
            channels=[NotificationChannel.IN_APP, NotificationChannel.SMS],
            metadata={
                'position_id': position_id,
                'symbol': symbol,
                'side': side,
                'stop_price': stop_price,
                'current_price': current_price,
                'trading_mode': trading_mode
            }
        )
        
        self.notification_service.create_notification(db, request)
        logger.info(f"Triggered trailing stop notification for user {user_id}")
    
    def trigger_investor_invitation(
        self,
        db: Session,
        user_id: str,
        inviter_name: str,
        account_name: str,
        invitation_link: str
    ):
        """
        Trigger notification when a user is invited as an investor.
        
        Args:
            db: Database session
            user_id: User ID (invitee)
            inviter_name: Name of the person who sent the invitation
            account_name: Name of the account
            invitation_link: Link to accept invitation
        """
        request = NotificationRequest(
            user_id=user_id,
            type=NotificationType.INVESTOR_INVITATION,
            title="Investor Invitation",
            message=f"{inviter_name} has invited you to view their trading account '{account_name}'. Click the link to accept: {invitation_link}",
            severity=NotificationSeverity.INFO,
            channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL],
            metadata={
                'inviter_name': inviter_name,
                'account_name': account_name,
                'invitation_link': invitation_link
            }
        )
        
        self.notification_service.create_notification(db, request)
        logger.info(f"Triggered investor invitation notification for user {user_id}")
    
    def trigger_account_access_granted(
        self,
        db: Session,
        user_id: str,
        account_name: str,
        granted_by: str
    ):
        """
        Trigger notification when investor access is granted to an account.
        
        Args:
            db: Database session
            user_id: User ID (investor)
            account_name: Name of the account
            granted_by: Name of the person who granted access
        """
        request = NotificationRequest(
            user_id=user_id,
            type=NotificationType.ACCOUNT_ACCESS_GRANTED,
            title="Account Access Granted",
            message=f"You now have investor access to trading account '{account_name}' granted by {granted_by}.",
            severity=NotificationSeverity.INFO,
            channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL],
            metadata={
                'account_name': account_name,
                'granted_by': granted_by
            }
        )
        
        self.notification_service.create_notification(db, request)
        logger.info(f"Triggered account access granted notification for user {user_id}")
    
    def trigger_session_timeout_warning(
        self,
        db: Session,
        user_id: str,
        minutes_remaining: int
    ):
        """
        Trigger notification warning about upcoming session timeout.
        
        Args:
            db: Database session
            user_id: User ID
            minutes_remaining: Minutes until session timeout
        """
        request = NotificationRequest(
            user_id=user_id,
            type=NotificationType.SESSION_TIMEOUT_WARNING,
            title="Session Timeout Warning",
            message=f"Your session will expire in {minutes_remaining} minutes due to inactivity. Please refresh to stay logged in.",
            severity=NotificationSeverity.WARNING,
            channels=[NotificationChannel.IN_APP],
            metadata={
                'minutes_remaining': minutes_remaining
            }
        )
        
        self.notification_service.create_notification(db, request)
        logger.info(f"Triggered session timeout warning for user {user_id}")
    
    def trigger_account_locked(
        self,
        db: Session,
        user_id: str,
        reason: str,
        unlock_time: Optional[datetime] = None
    ):
        """
        Trigger notification when account is locked.
        
        Args:
            db: Database session
            user_id: User ID
            reason: Reason for account lock
            unlock_time: Time when account will be automatically unlocked
        """
        message = f"Your account has been locked. Reason: {reason}"
        if unlock_time:
            message += f"\n\nYour account will be automatically unlocked at {unlock_time.strftime('%Y-%m-%d %H:%M:%S')}."
        
        request = NotificationRequest(
            user_id=user_id,
            type=NotificationType.ACCOUNT_LOCKED,
            title="Account Locked",
            message=message,
            severity=NotificationSeverity.ERROR,
            channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL],
            metadata={
                'reason': reason,
                'unlock_time': unlock_time.isoformat() if unlock_time else None
            }
        )
        
        self.notification_service.create_notification(db, request)
        logger.info(f"Triggered account locked notification for user {user_id}")
    
    def trigger_loss_limit_breached(
        self,
        db: Session,
        user_id: str,
        account_id: str,
        trading_mode: str,
        current_loss: float,
        loss_limit: float
    ):
        """
        Trigger notification when maximum loss limit is breached.
        
        Args:
            db: Database session
            user_id: User ID
            account_id: Account ID
            trading_mode: Trading mode (paper/live)
            current_loss: Current total loss
            loss_limit: Maximum loss limit
        """
        mode_label = "Paper" if trading_mode == "paper" else "Live"
        
        request = NotificationRequest(
            user_id=user_id,
            type=NotificationType.LOSS_LIMIT_BREACHED,
            title=f"{mode_label} Loss Limit Breached",
            message=f"Your {trading_mode} trading loss of ₹{abs(current_loss):.2f} has exceeded the maximum limit of ₹{abs(loss_limit):.2f}. All strategies have been paused. Please acknowledge and update your limit to continue trading.",
            severity=NotificationSeverity.CRITICAL,
            channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL, NotificationChannel.SMS],
            metadata={
                'account_id': account_id,
                'trading_mode': trading_mode,
                'current_loss': current_loss,
                'loss_limit': loss_limit
            }
        )
        
        self.notification_service.create_notification(db, request)
        logger.info(f"Triggered loss limit breached notification for user {user_id}")
    
    def trigger_strategy_paused(
        self,
        db: Session,
        user_id: str,
        strategy_id: str,
        strategy_name: str,
        reason: str,
        trading_mode: str
    ):
        """
        Trigger notification when a strategy is paused.
        
        Args:
            db: Database session
            user_id: User ID
            strategy_id: Strategy ID
            strategy_name: Strategy name
            reason: Reason for pause
            trading_mode: Trading mode (paper/live)
        """
        mode_label = "Paper" if trading_mode == "paper" else "Live"
        
        request = NotificationRequest(
            user_id=user_id,
            type=NotificationType.STRATEGY_PAUSED,
            title=f"{mode_label} Strategy Paused",
            message=f"Strategy '{strategy_name}' has been paused. Reason: {reason}",
            severity=NotificationSeverity.WARNING,
            channels=[NotificationChannel.IN_APP, NotificationChannel.EMAIL],
            metadata={
                'strategy_id': strategy_id,
                'strategy_name': strategy_name,
                'reason': reason,
                'trading_mode': trading_mode
            }
        )
        
        self.notification_service.create_notification(db, request)
        logger.info(f"Triggered strategy paused notification for user {user_id}")
    
    def trigger_system_alert(
        self,
        db: Session,
        user_id: str,
        alert_title: str,
        alert_message: str,
        severity: NotificationSeverity = NotificationSeverity.INFO
    ):
        """
        Trigger a generic system alert notification.
        
        Args:
            db: Database session
            user_id: User ID
            alert_title: Alert title
            alert_message: Alert message
            severity: Alert severity
        """
        request = NotificationRequest(
            user_id=user_id,
            type=NotificationType.SYSTEM_ALERT,
            title=alert_title,
            message=alert_message,
            severity=severity,
            channels=[NotificationChannel.IN_APP],
            metadata={}
        )
        
        self.notification_service.create_notification(db, request)
        logger.info(f"Triggered system alert notification for user {user_id}")


# Global notification triggers instance
_notification_triggers = None


def get_notification_triggers() -> NotificationTriggers:
    """Get or create the global notification triggers instance."""
    global _notification_triggers
    if _notification_triggers is None:
        _notification_triggers = NotificationTriggers()
    return _notification_triggers
