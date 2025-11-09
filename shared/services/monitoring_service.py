"""
Monitoring service for system health checks and alerting.
Tracks CPU, memory, database connections, and custom trading metrics.
"""
import logging
import psutil
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum

from shared.database.connection import get_db_manager
from shared.redis.connection import get_redis_client

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class Alert:
    """Alert data structure."""
    metric_name: str
    severity: AlertSeverity
    message: str
    current_value: float
    threshold: float
    timestamp: datetime


@dataclass
class MetricThreshold:
    """Threshold configuration for a metric."""
    metric_name: str
    threshold: float
    duration_seconds: int
    severity: AlertSeverity
    comparison: str  # 'gt' (greater than) or 'lt' (less than)


class MonitoringService:
    """Service for monitoring system health and generating alerts."""
    
    def __init__(self):
        """Initialize monitoring service."""
        self.redis = get_redis_client()
        self.alert_callbacks: List[Callable[[Alert], None]] = []
        
        # Default thresholds
        self.thresholds = {
            'cpu_percent': MetricThreshold(
                metric_name='cpu_percent',
                threshold=80.0,
                duration_seconds=300,  # 5 minutes
                severity=AlertSeverity.WARNING,
                comparison='gt'
            ),
            'memory_percent': MetricThreshold(
                metric_name='memory_percent',
                threshold=90.0,
                duration_seconds=300,
                severity=AlertSeverity.CRITICAL,
                comparison='gt'
            ),
            'disk_percent': MetricThreshold(
                metric_name='disk_percent',
                threshold=85.0,
                duration_seconds=600,  # 10 minutes
                severity=AlertSeverity.WARNING,
                comparison='gt'
            ),
            'db_pool_utilization': MetricThreshold(
                metric_name='db_pool_utilization',
                threshold=90.0,
                duration_seconds=60,
                severity=AlertSeverity.CRITICAL,
                comparison='gt'
            ),
            'error_rate': MetricThreshold(
                metric_name='error_rate',
                threshold=5.0,  # 5% error rate
                duration_seconds=300,
                severity=AlertSeverity.WARNING,
                comparison='gt'
            )
        }
    
    def register_alert_callback(self, callback: Callable[[Alert], None]) -> None:
        """
        Register a callback to be called when alerts are triggered.
        
        Args:
            callback: Function to call with Alert object
        """
        self.alert_callbacks.append(callback)
    
    def _trigger_alert(self, alert: Alert) -> None:
        """
        Trigger an alert by calling all registered callbacks.
        
        Args:
            alert: Alert to trigger
        """
        logger.warning(
            f"Alert triggered: {alert.metric_name} = {alert.current_value} "
            f"(threshold: {alert.threshold}, severity: {alert.severity.value})"
        )
        
        # Store alert in Redis
        alert_key = f"alert:{alert.metric_name}:{int(alert.timestamp.timestamp())}"
        self.redis.setex(
            alert_key,
            3600,  # Keep for 1 hour
            str({
                'metric': alert.metric_name,
                'severity': alert.severity.value,
                'message': alert.message,
                'value': alert.current_value,
                'threshold': alert.threshold,
                'timestamp': alert.timestamp.isoformat()
            })
        )
        
        # Call registered callbacks
        for callback in self.alert_callbacks:
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}", exc_info=True)
    
    def _check_threshold(
        self,
        metric_name: str,
        current_value: float
    ) -> Optional[Alert]:
        """
        Check if a metric exceeds its threshold.
        
        Args:
            metric_name: Name of the metric
            current_value: Current value of the metric
            
        Returns:
            Alert if threshold exceeded, None otherwise
        """
        threshold_config = self.thresholds.get(metric_name)
        if not threshold_config:
            return None
        
        # Check if threshold is exceeded
        exceeded = False
        if threshold_config.comparison == 'gt':
            exceeded = current_value > threshold_config.threshold
        elif threshold_config.comparison == 'lt':
            exceeded = current_value < threshold_config.threshold
        
        if not exceeded:
            # Clear any existing breach tracking
            self.redis.delete(f"metric_breach:{metric_name}")
            return None
        
        # Track breach duration
        breach_key = f"metric_breach:{metric_name}"
        breach_start = self.redis.get(breach_key)
        
        if not breach_start:
            # First time exceeding threshold
            self.redis.setex(
                breach_key,
                threshold_config.duration_seconds + 60,
                str(time.time())
            )
            return None
        
        # Check if breach duration exceeded
        breach_duration = time.time() - float(breach_start)
        if breach_duration >= threshold_config.duration_seconds:
            # Threshold exceeded for required duration
            alert = Alert(
                metric_name=metric_name,
                severity=threshold_config.severity,
                message=f"{metric_name} has been above {threshold_config.threshold} "
                        f"for {int(breach_duration)} seconds",
                current_value=current_value,
                threshold=threshold_config.threshold,
                timestamp=datetime.utcnow()
            )
            
            # Reset breach tracking to avoid repeated alerts
            self.redis.delete(breach_key)
            
            return alert
        
        return None
    
    def collect_cpu_metrics(self) -> Dict[str, Any]:
        """
        Collect CPU usage metrics.
        
        Returns:
            Dictionary with CPU metrics
        """
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        cpu_per_core = psutil.cpu_percent(interval=1, percpu=True)
        
        metrics = {
            'cpu_percent': cpu_percent,
            'cpu_count': cpu_count,
            'cpu_per_core': cpu_per_core,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Check threshold
        alert = self._check_threshold('cpu_percent', cpu_percent)
        if alert:
            self._trigger_alert(alert)
        
        # Store in Redis for time series
        self.redis.zadd(
            'metrics:cpu_percent',
            {str(cpu_percent): time.time()}
        )
        # Keep only last hour
        self.redis.zremrangebyscore(
            'metrics:cpu_percent',
            0,
            time.time() - 3600
        )
        
        return metrics
    
    def collect_memory_metrics(self) -> Dict[str, Any]:
        """
        Collect memory usage metrics.
        
        Returns:
            Dictionary with memory metrics
        """
        memory = psutil.virtual_memory()
        
        metrics = {
            'memory_percent': memory.percent,
            'memory_used_gb': memory.used / (1024 ** 3),
            'memory_total_gb': memory.total / (1024 ** 3),
            'memory_available_gb': memory.available / (1024 ** 3),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Check threshold
        alert = self._check_threshold('memory_percent', memory.percent)
        if alert:
            self._trigger_alert(alert)
        
        # Store in Redis
        self.redis.zadd(
            'metrics:memory_percent',
            {str(memory.percent): time.time()}
        )
        self.redis.zremrangebyscore(
            'metrics:memory_percent',
            0,
            time.time() - 3600
        )
        
        return metrics
    
    def collect_disk_metrics(self) -> Dict[str, Any]:
        """
        Collect disk usage metrics.
        
        Returns:
            Dictionary with disk metrics
        """
        disk = psutil.disk_usage('/')
        
        metrics = {
            'disk_percent': disk.percent,
            'disk_used_gb': disk.used / (1024 ** 3),
            'disk_total_gb': disk.total / (1024 ** 3),
            'disk_free_gb': disk.free / (1024 ** 3),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Check threshold
        alert = self._check_threshold('disk_percent', disk.percent)
        if alert:
            self._trigger_alert(alert)
        
        return metrics
    
    def collect_database_metrics(self) -> Dict[str, Any]:
        """
        Collect database connection pool metrics.
        
        Returns:
            Dictionary with database metrics
        """
        try:
            db_manager = get_db_manager()
            pool_status = db_manager.get_pool_status()
            
            pool_size = pool_status.get('size', 0)
            checked_out = pool_status.get('checked_out', 0)
            overflow = pool_status.get('overflow', 0)
            
            # Calculate utilization percentage
            total_capacity = pool_size + overflow
            utilization = (checked_out / total_capacity * 100) if total_capacity > 0 else 0
            
            metrics = {
                'db_pool_size': pool_size,
                'db_checked_out': checked_out,
                'db_overflow': overflow,
                'db_pool_utilization': utilization,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            # Check threshold
            alert = self._check_threshold('db_pool_utilization', utilization)
            if alert:
                self._trigger_alert(alert)
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting database metrics: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def collect_redis_metrics(self) -> Dict[str, Any]:
        """
        Collect Redis metrics.
        
        Returns:
            Dictionary with Redis metrics
        """
        try:
            info = self.redis.info()
            
            metrics = {
                'redis_used_memory_mb': info.get('used_memory', 0) / (1024 ** 2),
                'redis_connected_clients': info.get('connected_clients', 0),
                'redis_total_commands': info.get('total_commands_processed', 0),
                'redis_ops_per_sec': info.get('instantaneous_ops_per_sec', 0),
                'timestamp': datetime.utcnow().isoformat()
            }
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error collecting Redis metrics: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    def track_error_rate(self, service_name: str, is_error: bool) -> None:
        """
        Track error rate for a service.
        
        Args:
            service_name: Name of the service
            is_error: Whether this request was an error
        """
        key = f"errors:{service_name}"
        timestamp = time.time()
        
        # Add to sorted set with timestamp
        self.redis.zadd(key, {f"{int(is_error)}:{timestamp}": timestamp})
        
        # Remove old entries (older than 5 minutes)
        self.redis.zremrangebyscore(key, 0, timestamp - 300)
        
        # Calculate error rate
        all_requests = self.redis.zcard(key)
        if all_requests > 0:
            errors = len([
                x for x in self.redis.zrange(key, 0, -1)
                if x.decode().startswith('1:')
            ])
            error_rate = (errors / all_requests) * 100
            
            # Check threshold
            alert = self._check_threshold('error_rate', error_rate)
            if alert:
                alert.message = f"{service_name} error rate is {error_rate:.2f}%"
                self._trigger_alert(alert)
    
    def track_custom_metric(
        self,
        metric_name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Track a custom metric.
        
        Args:
            metric_name: Name of the metric
            value: Metric value
            tags: Optional tags for the metric
        """
        key = f"custom_metric:{metric_name}"
        if tags:
            tag_str = ':'.join(f"{k}={v}" for k, v in tags.items())
            key = f"{key}:{tag_str}"
        
        self.redis.zadd(key, {str(value): time.time()})
        
        # Keep only last hour
        self.redis.zremrangebyscore(key, 0, time.time() - 3600)
    
    def get_metric_history(
        self,
        metric_name: str,
        duration_seconds: int = 3600
    ) -> List[Dict[str, Any]]:
        """
        Get historical values for a metric.
        
        Args:
            metric_name: Name of the metric
            duration_seconds: How far back to look
            
        Returns:
            List of metric values with timestamps
        """
        key = f"metrics:{metric_name}"
        cutoff = time.time() - duration_seconds
        
        values = self.redis.zrangebyscore(key, cutoff, '+inf', withscores=True)
        
        return [
            {
                'value': float(value.decode()),
                'timestamp': datetime.fromtimestamp(score).isoformat()
            }
            for value, score in values
        ]
    
    def get_recent_alerts(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get recent alerts.
        
        Args:
            limit: Maximum number of alerts to return
            
        Returns:
            List of recent alerts
        """
        # Scan for alert keys
        alerts = []
        for key in self.redis.scan_iter("alert:*"):
            alert_data = self.redis.get(key)
            if alert_data:
                try:
                    alerts.append(eval(alert_data.decode()))
                except Exception as e:
                    logger.error(f"Error parsing alert data: {e}")
        
        # Sort by timestamp (most recent first)
        alerts.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return alerts[:limit]
    
    def collect_all_metrics(self) -> Dict[str, Any]:
        """
        Collect all system metrics.
        
        Returns:
            Dictionary with all metrics
        """
        return {
            'cpu': self.collect_cpu_metrics(),
            'memory': self.collect_memory_metrics(),
            'disk': self.collect_disk_metrics(),
            'database': self.collect_database_metrics(),
            'redis': self.collect_redis_metrics(),
            'timestamp': datetime.utcnow().isoformat()
        }


# Global monitoring service instance
_monitoring_service = None


def get_monitoring_service() -> MonitoringService:
    """Get or create the global monitoring service instance."""
    global _monitoring_service
    if _monitoring_service is None:
        _monitoring_service = MonitoringService()
    return _monitoring_service
