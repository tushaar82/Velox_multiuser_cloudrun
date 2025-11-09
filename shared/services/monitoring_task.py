"""
Background task for continuous system monitoring.
Collects metrics at regular intervals and triggers alerts.
"""
import logging
import time
import threading
from typing import Optional

from shared.services.monitoring_service import get_monitoring_service, Alert
from shared.services.notification_service import NotificationService
from shared.database.connection import get_db_session

logger = logging.getLogger(__name__)


class MonitoringTask:
    """Background task for continuous monitoring."""
    
    def __init__(self, interval_seconds: int = 60):
        """
        Initialize monitoring task.
        
        Args:
            interval_seconds: Interval between metric collections
        """
        self.interval_seconds = interval_seconds
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.monitoring_service = get_monitoring_service()
        
        # Register alert callback
        self.monitoring_service.register_alert_callback(self._handle_alert)
    
    def _handle_alert(self, alert: Alert) -> None:
        """
        Handle triggered alerts by sending notifications to admins.
        
        Args:
            alert: Alert that was triggered
        """
        try:
            # Get database session
            db = get_db_session()
            
            # Get notification service
            notification_service = NotificationService(db)
            
            # Get all admin users
            from shared.models import User, UserRole
            admins = db.query(User).filter(User.role == UserRole.ADMIN).all()
            
            # Send notification to each admin
            for admin in admins:
                try:
                    notification_service.send_notification(
                        user_id=str(admin.id),
                        notification_type='system_alert',
                        title=f"System Alert: {alert.metric_name}",
                        message=alert.message,
                        severity=alert.severity.value,
                        channels=['in_app', 'email'] if alert.severity.value == 'critical' else ['in_app']
                    )
                except Exception as e:
                    logger.error(f"Error sending alert notification to admin {admin.id}: {e}")
            
            db.close()
            
        except Exception as e:
            logger.error(f"Error handling alert: {e}", exc_info=True)
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop that runs in background thread."""
        logger.info("Monitoring task started")
        
        while self.running:
            try:
                # Collect all metrics
                metrics = self.monitoring_service.collect_all_metrics()
                
                logger.debug(f"Collected metrics: CPU={metrics['cpu']['cpu_percent']}%, "
                           f"Memory={metrics['memory']['memory_percent']}%")
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}", exc_info=True)
            
            # Sleep until next interval
            time.sleep(self.interval_seconds)
        
        logger.info("Monitoring task stopped")
    
    def start(self) -> None:
        """Start the monitoring task in a background thread."""
        if self.running:
            logger.warning("Monitoring task is already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.thread.start()
        logger.info(f"Monitoring task started with {self.interval_seconds}s interval")
    
    def stop(self) -> None:
        """Stop the monitoring task."""
        if not self.running:
            logger.warning("Monitoring task is not running")
            return
        
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Monitoring task stopped")


# Global monitoring task instance
_monitoring_task = None


def get_monitoring_task(interval_seconds: int = 60) -> MonitoringTask:
    """
    Get or create the global monitoring task instance.
    
    Args:
        interval_seconds: Interval between metric collections
        
    Returns:
        MonitoringTask instance
    """
    global _monitoring_task
    if _monitoring_task is None:
        _monitoring_task = MonitoringTask(interval_seconds=interval_seconds)
    return _monitoring_task


def start_monitoring() -> None:
    """Start the global monitoring task."""
    task = get_monitoring_task()
    task.start()


def stop_monitoring() -> None:
    """Stop the global monitoring task."""
    task = get_monitoring_task()
    task.stop()
