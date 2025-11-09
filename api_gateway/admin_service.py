"""
Admin service for system monitoring, user management, and data aggregation.
Provides admin-only functionality for platform oversight.
"""
import logging
import psutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from shared.models import (
    User, UserAccount, Order, Trade, Position,
    UserRole, OrderStatus, TradingMode
)
from shared.database.connection import get_db_manager
from shared.redis.connection import get_redis_client

logger = logging.getLogger(__name__)


class AdminServiceError(Exception):
    """Base exception for admin service errors."""
    pass


class UnauthorizedAdminAccessError(AdminServiceError):
    """Raised when non-admin tries to access admin functionality."""
    pass


class AdminService:
    """Service for admin dashboard and monitoring functionality."""
    
    def __init__(self, db_session: Session):
        """
        Initialize admin service.
        
        Args:
            db_session: Database session for queries
        """
        self.db = db_session
        try:
            self.redis = get_redis_client()
        except RuntimeError:
            # Redis not initialized (e.g., in tests)
            self.redis = None
    
    def _verify_admin(self, user_id: str) -> User:
        """
        Verify that user is an admin.
        
        Args:
            user_id: User ID to verify
            
        Returns:
            User object if admin
            
        Raises:
            UnauthorizedAdminAccessError: If user is not admin
        """
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user or user.role != UserRole.ADMIN:
            raise UnauthorizedAdminAccessError("Admin access required")
        return user
    
    def get_active_user_count_by_role(self, admin_id: str) -> Dict[str, int]:
        """
        Get count of active users by role.
        
        Args:
            admin_id: Admin user ID
            
        Returns:
            Dictionary with role counts
            
        Raises:
            UnauthorizedAdminAccessError: If not admin
        """
        self._verify_admin(admin_id)
        
        # Query user counts by role
        counts = self.db.query(
            User.role,
            func.count(User.id).label('count')
        ).filter(
            User.is_locked == False
        ).group_by(User.role).all()
        
        result = {
            'admin': 0,
            'trader': 0,
            'investor': 0,
            'total': 0
        }
        
        for role, count in counts:
            result[role.value] = count
            result['total'] += count
        
        logger.info(f"Admin {admin_id} retrieved user counts: {result}")
        return result
    
    def get_total_orders_processed(
        self,
        admin_id: str,
        time_period: Optional[str] = 'today'
    ) -> Dict[str, Any]:
        """
        Get total orders processed with breakdown by status and trading mode.
        
        Args:
            admin_id: Admin user ID
            time_period: Time period ('today', 'week', 'month', 'all')
            
        Returns:
            Dictionary with order statistics
            
        Raises:
            UnauthorizedAdminAccessError: If not admin
        """
        self._verify_admin(admin_id)
        
        # Calculate time filter
        now = datetime.utcnow()
        if time_period == 'today':
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_period == 'week':
            start_time = now - timedelta(days=7)
        elif time_period == 'month':
            start_time = now - timedelta(days=30)
        else:
            start_time = None
        
        # Build query
        query = self.db.query(Order)
        if start_time:
            query = query.filter(Order.created_at >= start_time)
        
        # Total orders
        total_orders = query.count()
        
        # Orders by status
        status_counts = query.with_entities(
            Order.status,
            func.count(Order.id).label('count')
        ).group_by(Order.status).all()
        
        by_status = {status.value: count for status, count in status_counts}
        
        # Orders by trading mode
        mode_counts = query.with_entities(
            Order.trading_mode,
            func.count(Order.id).label('count')
        ).group_by(Order.trading_mode).all()
        
        by_mode = {mode.value: count for mode, count in mode_counts}
        
        result = {
            'total_orders': total_orders,
            'by_status': by_status,
            'by_trading_mode': by_mode,
            'time_period': time_period,
            'start_time': start_time.isoformat() if start_time else None
        }
        
        logger.info(f"Admin {admin_id} retrieved order statistics for {time_period}")
        return result
    
    def get_system_resource_utilization(self, admin_id: str) -> Dict[str, Any]:
        """
        Get current system resource utilization metrics.
        
        Args:
            admin_id: Admin user ID
            
        Returns:
            Dictionary with resource metrics
            
        Raises:
            UnauthorizedAdminAccessError: If not admin
        """
        self._verify_admin(admin_id)
        
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_used_gb = memory.used / (1024 ** 3)
        memory_total_gb = memory.total / (1024 ** 3)
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_percent = disk.percent
        disk_used_gb = disk.used / (1024 ** 3)
        disk_total_gb = disk.total / (1024 ** 3)
        
        # Database connections
        try:
            db_manager = get_db_manager()
            pool_status = db_manager.get_pool_status()
            db_pool_size = pool_status.get('size')
            db_pool_checked_out = pool_status.get('checked_out')
            db_pool_overflow = pool_status.get('overflow')
        except Exception as e:
            logger.error(f"Error getting database pool stats: {e}")
            db_pool_size = None
            db_pool_checked_out = None
            db_pool_overflow = None
        
        # Redis info
        try:
            redis_info = self.redis.info()
            redis_used_memory_mb = redis_info.get('used_memory', 0) / (1024 ** 2)
            redis_connected_clients = redis_info.get('connected_clients', 0)
        except Exception as e:
            logger.error(f"Error getting Redis stats: {e}")
            redis_used_memory_mb = None
            redis_connected_clients = None
        
        result = {
            'cpu': {
                'percent': cpu_percent,
                'count': cpu_count
            },
            'memory': {
                'percent': memory_percent,
                'used_gb': round(memory_used_gb, 2),
                'total_gb': round(memory_total_gb, 2)
            },
            'disk': {
                'percent': disk_percent,
                'used_gb': round(disk_used_gb, 2),
                'total_gb': round(disk_total_gb, 2)
            },
            'database': {
                'pool_size': db_pool_size,
                'checked_out': db_pool_checked_out,
                'overflow': db_pool_overflow
            },
            'redis': {
                'used_memory_mb': round(redis_used_memory_mb, 2) if redis_used_memory_mb else None,
                'connected_clients': redis_connected_clients
            },
            'timestamp': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Admin {admin_id} retrieved system resource utilization")
        return result
    
    def get_trading_activity_summary(
        self,
        admin_id: str,
        time_period: Optional[str] = 'today'
    ) -> Dict[str, Any]:
        """
        Get summary of trading activity across all accounts.
        
        Args:
            admin_id: Admin user ID
            time_period: Time period ('today', 'week', 'month', 'all')
            
        Returns:
            Dictionary with trading activity metrics
            
        Raises:
            UnauthorizedAdminAccessError: If not admin
        """
        self._verify_admin(admin_id)
        
        # Calculate time filter
        now = datetime.utcnow()
        if time_period == 'today':
            start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_period == 'week':
            start_time = now - timedelta(days=7)
        elif time_period == 'month':
            start_time = now - timedelta(days=30)
        else:
            start_time = None
        
        # Total trades
        trade_query = self.db.query(Trade)
        if start_time:
            trade_query = trade_query.filter(Trade.executed_at >= start_time)
        
        total_trades = trade_query.count()
        
        # Trades by mode
        trades_by_mode = trade_query.with_entities(
            Trade.trading_mode,
            func.count(Trade.id).label('count'),
            func.sum(Trade.quantity * Trade.price).label('volume')
        ).group_by(Trade.trading_mode).all()
        
        by_mode = {}
        for mode, count, volume in trades_by_mode:
            by_mode[mode.value] = {
                'count': count,
                'volume': float(volume) if volume else 0
            }
        
        # Active positions
        active_positions = self.db.query(Position).filter(
            Position.closed_at.is_(None)
        ).count()
        
        # Active positions by mode
        positions_by_mode = self.db.query(
            Position.trading_mode,
            func.count(Position.id).label('count')
        ).filter(
            Position.closed_at.is_(None)
        ).group_by(Position.trading_mode).all()
        
        active_by_mode = {mode.value: count for mode, count in positions_by_mode}
        
        # Total P&L
        pnl_query = self.db.query(
            func.sum(Position.realized_pnl).label('realized'),
            func.sum(Position.unrealized_pnl).label('unrealized')
        )
        if start_time:
            pnl_query = pnl_query.filter(Position.opened_at >= start_time)
        
        pnl_result = pnl_query.first()
        total_realized_pnl = float(pnl_result.realized) if pnl_result.realized else 0
        total_unrealized_pnl = float(pnl_result.unrealized) if pnl_result.unrealized else 0
        
        result = {
            'total_trades': total_trades,
            'trades_by_mode': by_mode,
            'active_positions': active_positions,
            'active_positions_by_mode': active_by_mode,
            'total_realized_pnl': total_realized_pnl,
            'total_unrealized_pnl': total_unrealized_pnl,
            'total_pnl': total_realized_pnl + total_unrealized_pnl,
            'time_period': time_period,
            'start_time': start_time.isoformat() if start_time else None
        }
        
        logger.info(f"Admin {admin_id} retrieved trading activity summary for {time_period}")
        return result
    
    def get_all_user_accounts_with_activity(
        self,
        admin_id: str,
        include_inactive: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get all user accounts with recent activity metrics.
        
        Args:
            admin_id: Admin user ID
            include_inactive: Include inactive accounts
            
        Returns:
            List of account dictionaries with activity
            
        Raises:
            UnauthorizedAdminAccessError: If not admin
        """
        self._verify_admin(admin_id)
        
        # Query accounts
        query = self.db.query(UserAccount)
        if not include_inactive:
            query = query.filter(UserAccount.is_active == True)
        
        accounts = query.all()
        
        result = []
        for account in accounts:
            # Get trader info
            trader = account.trader
            
            # Count active strategies (would need active_strategies table)
            # For now, we'll skip this or use a placeholder
            
            # Count orders (last 30 days)
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            order_count = self.db.query(func.count(Order.id)).filter(
                Order.account_id == account.id,
                Order.created_at >= thirty_days_ago
            ).scalar()
            
            # Count trades (last 30 days)
            trade_count = self.db.query(func.count(Trade.id)).filter(
                Trade.account_id == account.id,
                Trade.executed_at >= thirty_days_ago
            ).scalar()
            
            # Active positions
            active_positions = self.db.query(func.count(Position.id)).filter(
                Position.account_id == account.id,
                Position.closed_at.is_(None)
            ).scalar()
            
            # Total P&L
            pnl = self.db.query(
                func.sum(Position.realized_pnl).label('realized'),
                func.sum(Position.unrealized_pnl).label('unrealized')
            ).filter(
                Position.account_id == account.id
            ).first()
            
            result.append({
                'account_id': str(account.id),
                'account_name': account.name,
                'trader_email': trader.email if trader else None,
                'is_active': account.is_active,
                'created_at': account.created_at.isoformat(),
                'activity': {
                    'orders_30d': order_count,
                    'trades_30d': trade_count,
                    'active_positions': active_positions,
                    'realized_pnl': float(pnl.realized) if pnl.realized else 0,
                    'unrealized_pnl': float(pnl.unrealized) if pnl.unrealized else 0
                }
            })
        
        logger.info(f"Admin {admin_id} retrieved {len(result)} user accounts")
        return result
    
    def get_account_trading_activity(
        self,
        admin_id: str,
        account_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get detailed trading activity for a specific account (read-only).
        
        Args:
            admin_id: Admin user ID
            account_id: Account to view
            start_date: Start date for activity
            end_date: End date for activity
            
        Returns:
            Dictionary with account trading activity
            
        Raises:
            UnauthorizedAdminAccessError: If not admin
        """
        self._verify_admin(admin_id)
        
        # Default to last 30 days if no dates provided
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=30)
        
        # Get account
        account = self.db.query(UserAccount).filter(
            UserAccount.id == account_id
        ).first()
        
        if not account:
            raise AdminServiceError("Account not found")
        
        # Get orders
        orders = self.db.query(Order).filter(
            Order.account_id == account_id,
            Order.created_at >= start_date,
            Order.created_at <= end_date
        ).order_by(Order.created_at.desc()).limit(100).all()
        
        # Get trades
        trades = self.db.query(Trade).filter(
            Trade.account_id == account_id,
            Trade.executed_at >= start_date,
            Trade.executed_at <= end_date
        ).order_by(Trade.executed_at.desc()).limit(100).all()
        
        # Get positions
        positions = self.db.query(Position).filter(
            Position.account_id == account_id,
            Position.opened_at >= start_date
        ).order_by(Position.opened_at.desc()).limit(50).all()
        
        result = {
            'account_id': str(account.id),
            'account_name': account.name,
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'orders': [
                {
                    'id': str(order.id),
                    'symbol': order.symbol,
                    'side': order.side.value,
                    'quantity': order.quantity,
                    'order_type': order.order_type.value,
                    'status': order.status.value,
                    'trading_mode': order.trading_mode.value,
                    'created_at': order.created_at.isoformat()
                }
                for order in orders
            ],
            'trades': [
                {
                    'id': str(trade.id),
                    'symbol': trade.symbol,
                    'side': trade.side.value,
                    'quantity': trade.quantity,
                    'price': float(trade.price),
                    'trading_mode': trade.trading_mode.value,
                    'executed_at': trade.executed_at.isoformat()
                }
                for trade in trades
            ],
            'positions': [
                {
                    'id': str(pos.id),
                    'symbol': pos.symbol,
                    'side': pos.side.value,
                    'quantity': pos.quantity,
                    'entry_price': float(pos.entry_price),
                    'unrealized_pnl': float(pos.unrealized_pnl),
                    'realized_pnl': float(pos.realized_pnl),
                    'trading_mode': pos.trading_mode.value,
                    'opened_at': pos.opened_at.isoformat(),
                    'closed_at': pos.closed_at.isoformat() if pos.closed_at else None
                }
                for pos in positions
            ]
        }
        
        logger.info(f"Admin {admin_id} viewed trading activity for account {account_id}")
        return result
    
    def get_audit_logs(
        self,
        admin_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_id: Optional[str] = None,
        action_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get audit logs for system activities.
        
        Args:
            admin_id: Admin user ID
            start_date: Start date for logs
            end_date: End date for logs
            user_id: Filter by specific user
            action_type: Filter by action type
            limit: Maximum number of logs to return
            
        Returns:
            List of audit log entries
            
        Raises:
            UnauthorizedAdminAccessError: If not admin
        """
        self._verify_admin(admin_id)
        
        # For now, we'll return authentication logs from sessions
        # In a full implementation, we'd have a dedicated audit_logs table
        
        # Default to last 7 days if no dates provided
        if not end_date:
            end_date = datetime.utcnow()
        if not start_date:
            start_date = end_date - timedelta(days=7)
        
        # Get session creation logs as a proxy for audit logs
        from shared.models import Session as UserSession
        
        query = self.db.query(UserSession).filter(
            UserSession.created_at >= start_date,
            UserSession.created_at <= end_date
        )
        
        if user_id:
            query = query.filter(UserSession.user_id == user_id)
        
        sessions = query.order_by(UserSession.created_at.desc()).limit(limit).all()
        
        logs = []
        for session in sessions:
            user = session.user
            logs.append({
                'timestamp': session.created_at.isoformat(),
                'user_id': str(session.user_id),
                'user_email': user.email if user else None,
                'action': 'login',
                'ip_address': session.ip_address,
                'user_agent': session.user_agent,
                'result': 'success'
            })
        
        logger.info(f"Admin {admin_id} retrieved {len(logs)} audit log entries")
        return logs
    
    def generate_daily_activity_report(
        self,
        admin_id: str,
        report_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Generate a daily activity report.
        
        Args:
            admin_id: Admin user ID
            report_date: Date for the report (defaults to yesterday)
            
        Returns:
            Dictionary with daily report data
            
        Raises:
            UnauthorizedAdminAccessError: If not admin
        """
        self._verify_admin(admin_id)
        
        # Default to yesterday
        if not report_date:
            report_date = datetime.utcnow() - timedelta(days=1)
        
        # Set time range for the day
        start_time = report_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=1)
        
        # User activity
        from shared.models import Session as UserSession
        
        active_users = self.db.query(func.count(func.distinct(UserSession.user_id))).filter(
            UserSession.created_at >= start_time,
            UserSession.created_at < end_time
        ).scalar()
        
        # Order activity
        total_orders = self.db.query(func.count(Order.id)).filter(
            Order.created_at >= start_time,
            Order.created_at < end_time
        ).scalar()
        
        filled_orders = self.db.query(func.count(Order.id)).filter(
            Order.created_at >= start_time,
            Order.created_at < end_time,
            Order.status == OrderStatus.FILLED
        ).scalar()
        
        # Trade activity
        total_trades = self.db.query(func.count(Trade.id)).filter(
            Trade.executed_at >= start_time,
            Trade.executed_at < end_time
        ).scalar()
        
        total_volume = self.db.query(
            func.sum(Trade.quantity * Trade.price)
        ).filter(
            Trade.executed_at >= start_time,
            Trade.executed_at < end_time
        ).scalar()
        
        # P&L for the day
        daily_pnl = self.db.query(
            func.sum(Position.realized_pnl)
        ).filter(
            Position.closed_at >= start_time,
            Position.closed_at < end_time
        ).scalar()
        
        # Error counts (would need error logging table)
        # For now, we'll use a placeholder
        
        report = {
            'report_date': report_date.date().isoformat(),
            'period': {
                'start': start_time.isoformat(),
                'end': end_time.isoformat()
            },
            'user_activity': {
                'active_users': active_users or 0
            },
            'order_activity': {
                'total_orders': total_orders or 0,
                'filled_orders': filled_orders or 0,
                'fill_rate': (filled_orders / total_orders * 100) if total_orders else 0
            },
            'trade_activity': {
                'total_trades': total_trades or 0,
                'total_volume': float(total_volume) if total_volume else 0
            },
            'pnl': {
                'daily_realized_pnl': float(daily_pnl) if daily_pnl else 0
            },
            'generated_at': datetime.utcnow().isoformat()
        }
        
        logger.info(f"Admin {admin_id} generated daily report for {report_date.date()}")
        return report
