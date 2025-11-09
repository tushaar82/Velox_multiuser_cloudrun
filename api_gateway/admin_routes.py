"""
Admin API routes for system monitoring and user management.
Provides endpoints for admin dashboard functionality.
"""
import logging
from datetime import datetime
from typing import Optional
from flask import Blueprint, request, jsonify
from sqlalchemy.orm import Session

from shared.database.connection import get_db_session
from api_gateway.admin_service import (
    AdminService,
    UnauthorizedAdminAccessError,
    AdminServiceError
)
from api_gateway.middleware import require_auth
from shared.services.monitoring_service import get_monitoring_service

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')


@admin_bp.route('/health', methods=['GET'])
@require_auth
def get_system_health():
    """
    Get system health dashboard data.
    
    Returns:
        JSON with system metrics
    """
    try:
        user_id = request.user_id
        db: Session = get_db_session()
        service = AdminService(db)
        
        # Get all metrics
        user_counts = service.get_active_user_count_by_role(user_id)
        orders = service.get_total_orders_processed(user_id, time_period='today')
        resources = service.get_system_resource_utilization(user_id)
        trading = service.get_trading_activity_summary(user_id, time_period='today')
        
        result = {
            'users': user_counts,
            'orders': orders,
            'resources': resources,
            'trading': trading,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return jsonify(result), 200
        
    except UnauthorizedAdminAccessError as e:
        logger.warning(f"Unauthorized admin access attempt: {e}")
        return jsonify({'error': 'Admin access required'}), 403
    except Exception as e:
        logger.error(f"Error getting system health: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        db.close()


@admin_bp.route('/users/count', methods=['GET'])
@require_auth
def get_user_count():
    """
    Get active user count by role.
    
    Returns:
        JSON with user counts
    """
    try:
        user_id = request.user_id
        db: Session = get_db_session()
        service = AdminService(db)
        
        result = service.get_active_user_count_by_role(user_id)
        return jsonify(result), 200
        
    except UnauthorizedAdminAccessError as e:
        logger.warning(f"Unauthorized admin access attempt: {e}")
        return jsonify({'error': 'Admin access required'}), 403
    except Exception as e:
        logger.error(f"Error getting user count: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        db.close()


@admin_bp.route('/orders/stats', methods=['GET'])
@require_auth
def get_order_stats():
    """
    Get order statistics.
    
    Query Parameters:
        period: Time period ('today', 'week', 'month', 'all')
    
    Returns:
        JSON with order statistics
    """
    try:
        user_id = request.user_id
        period = request.args.get('period', 'today')
        
        db: Session = get_db_session()
        service = AdminService(db)
        
        result = service.get_total_orders_processed(user_id, time_period=period)
        return jsonify(result), 200
        
    except UnauthorizedAdminAccessError as e:
        logger.warning(f"Unauthorized admin access attempt: {e}")
        return jsonify({'error': 'Admin access required'}), 403
    except Exception as e:
        logger.error(f"Error getting order stats: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        db.close()


@admin_bp.route('/resources', methods=['GET'])
@require_auth
def get_resources():
    """
    Get system resource utilization.
    
    Returns:
        JSON with resource metrics
    """
    try:
        user_id = request.user_id
        db: Session = get_db_session()
        service = AdminService(db)
        
        result = service.get_system_resource_utilization(user_id)
        return jsonify(result), 200
        
    except UnauthorizedAdminAccessError as e:
        logger.warning(f"Unauthorized admin access attempt: {e}")
        return jsonify({'error': 'Admin access required'}), 403
    except Exception as e:
        logger.error(f"Error getting resource utilization: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        db.close()


@admin_bp.route('/trading/summary', methods=['GET'])
@require_auth
def get_trading_summary():
    """
    Get trading activity summary.
    
    Query Parameters:
        period: Time period ('today', 'week', 'month', 'all')
    
    Returns:
        JSON with trading activity metrics
    """
    try:
        user_id = request.user_id
        period = request.args.get('period', 'today')
        
        db: Session = get_db_session()
        service = AdminService(db)
        
        result = service.get_trading_activity_summary(user_id, time_period=period)
        return jsonify(result), 200
        
    except UnauthorizedAdminAccessError as e:
        logger.warning(f"Unauthorized admin access attempt: {e}")
        return jsonify({'error': 'Admin access required'}), 403
    except Exception as e:
        logger.error(f"Error getting trading summary: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        db.close()


@admin_bp.route('/accounts', methods=['GET'])
@require_auth
def get_all_accounts():
    """
    Get all user accounts with activity metrics.
    
    Query Parameters:
        include_inactive: Include inactive accounts (default: false)
    
    Returns:
        JSON with list of accounts
    """
    try:
        user_id = request.user_id
        include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'
        
        db: Session = get_db_session()
        service = AdminService(db)
        
        result = service.get_all_user_accounts_with_activity(
            user_id,
            include_inactive=include_inactive
        )
        return jsonify({'accounts': result}), 200
        
    except UnauthorizedAdminAccessError as e:
        logger.warning(f"Unauthorized admin access attempt: {e}")
        return jsonify({'error': 'Admin access required'}), 403
    except Exception as e:
        logger.error(f"Error getting accounts: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        db.close()


@admin_bp.route('/accounts/<account_id>/activity', methods=['GET'])
@require_auth
def get_account_activity(account_id: str):
    """
    Get trading activity for a specific account (read-only).
    
    Query Parameters:
        start_date: Start date (ISO format)
        end_date: End date (ISO format)
    
    Returns:
        JSON with account trading activity
    """
    try:
        user_id = request.user_id
        
        # Parse dates
        start_date = None
        end_date = None
        if request.args.get('start_date'):
            start_date = datetime.fromisoformat(request.args.get('start_date'))
        if request.args.get('end_date'):
            end_date = datetime.fromisoformat(request.args.get('end_date'))
        
        db: Session = get_db_session()
        service = AdminService(db)
        
        result = service.get_account_trading_activity(
            user_id,
            account_id,
            start_date=start_date,
            end_date=end_date
        )
        return jsonify(result), 200
        
    except UnauthorizedAdminAccessError as e:
        logger.warning(f"Unauthorized admin access attempt: {e}")
        return jsonify({'error': 'Admin access required'}), 403
    except AdminServiceError as e:
        logger.warning(f"Admin service error: {e}")
        return jsonify({'error': str(e)}), 400
    except ValueError as e:
        logger.warning(f"Invalid date format: {e}")
        return jsonify({'error': 'Invalid date format. Use ISO format (YYYY-MM-DD)'}), 400
    except Exception as e:
        logger.error(f"Error getting account activity: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        db.close()


@admin_bp.route('/users/<user_id>/disable', methods=['POST'])
@require_auth
def disable_user(user_id: str):
    """
    Disable a user account.
    
    Returns:
        JSON with success message
    """
    try:
        admin_id = request.user_id
        db: Session = get_db_session()
        
        # Import user service for user management
        from api_gateway.user_service import UserService
        user_service = UserService(db)
        
        success = user_service.disable_user(user_id, admin_id)
        
        if success:
            return jsonify({'message': 'User disabled successfully'}), 200
        else:
            return jsonify({'error': 'User not found'}), 404
        
    except UnauthorizedAdminAccessError as e:
        logger.warning(f"Unauthorized admin access attempt: {e}")
        return jsonify({'error': 'Admin access required'}), 403
    except Exception as e:
        logger.error(f"Error disabling user: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        db.close()


@admin_bp.route('/users/<user_id>/enable', methods=['POST'])
@require_auth
def enable_user(user_id: str):
    """
    Enable a user account.
    
    Returns:
        JSON with success message
    """
    try:
        admin_id = request.user_id
        db: Session = get_db_session()
        
        # Import user service for user management
        from api_gateway.user_service import UserService
        user_service = UserService(db)
        
        success = user_service.enable_user(user_id, admin_id)
        
        if success:
            return jsonify({'message': 'User enabled successfully'}), 200
        else:
            return jsonify({'error': 'User not found'}), 404
        
    except UnauthorizedAdminAccessError as e:
        logger.warning(f"Unauthorized admin access attempt: {e}")
        return jsonify({'error': 'Admin access required'}), 403
    except Exception as e:
        logger.error(f"Error enabling user: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        db.close()



@admin_bp.route('/monitoring/metrics', methods=['GET'])
@require_auth
def get_monitoring_metrics():
    """
    Get current system monitoring metrics.
    
    Returns:
        JSON with all system metrics
    """
    try:
        user_id = request.user_id
        db: Session = get_db_session()
        service = AdminService(db)
        
        # Verify admin access
        service._verify_admin(user_id)
        
        # Get monitoring metrics
        monitoring = get_monitoring_service()
        metrics = monitoring.collect_all_metrics()
        
        return jsonify(metrics), 200
        
    except UnauthorizedAdminAccessError as e:
        logger.warning(f"Unauthorized admin access attempt: {e}")
        return jsonify({'error': 'Admin access required'}), 403
    except Exception as e:
        logger.error(f"Error getting monitoring metrics: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        db.close()


@admin_bp.route('/monitoring/alerts', methods=['GET'])
@require_auth
def get_recent_alerts():
    """
    Get recent system alerts.
    
    Query Parameters:
        limit: Maximum number of alerts to return (default: 50)
    
    Returns:
        JSON with recent alerts
    """
    try:
        user_id = request.user_id
        limit = int(request.args.get('limit', 50))
        
        db: Session = get_db_session()
        service = AdminService(db)
        
        # Verify admin access
        service._verify_admin(user_id)
        
        # Get recent alerts
        monitoring = get_monitoring_service()
        alerts = monitoring.get_recent_alerts(limit=limit)
        
        return jsonify({'alerts': alerts}), 200
        
    except UnauthorizedAdminAccessError as e:
        logger.warning(f"Unauthorized admin access attempt: {e}")
        return jsonify({'error': 'Admin access required'}), 403
    except Exception as e:
        logger.error(f"Error getting alerts: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        db.close()


@admin_bp.route('/monitoring/metrics/<metric_name>/history', methods=['GET'])
@require_auth
def get_metric_history(metric_name: str):
    """
    Get historical values for a specific metric.
    
    Query Parameters:
        duration: Duration in seconds (default: 3600)
    
    Returns:
        JSON with metric history
    """
    try:
        user_id = request.user_id
        duration = int(request.args.get('duration', 3600))
        
        db: Session = get_db_session()
        service = AdminService(db)
        
        # Verify admin access
        service._verify_admin(user_id)
        
        # Get metric history
        monitoring = get_monitoring_service()
        history = monitoring.get_metric_history(metric_name, duration_seconds=duration)
        
        return jsonify({
            'metric_name': metric_name,
            'duration_seconds': duration,
            'history': history
        }), 200
        
    except UnauthorizedAdminAccessError as e:
        logger.warning(f"Unauthorized admin access attempt: {e}")
        return jsonify({'error': 'Admin access required'}), 403
    except Exception as e:
        logger.error(f"Error getting metric history: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        db.close()



@admin_bp.route('/audit-logs', methods=['GET'])
@require_auth
def get_audit_logs():
    """
    Get audit logs for system activities.
    
    Query Parameters:
        start_date: Start date (ISO format)
        end_date: End date (ISO format)
        user_id: Filter by specific user
        action_type: Filter by action type
        limit: Maximum number of logs (default: 100)
    
    Returns:
        JSON with audit logs
    """
    try:
        user_id = request.user_id
        
        # Parse parameters
        start_date = None
        end_date = None
        if request.args.get('start_date'):
            start_date = datetime.fromisoformat(request.args.get('start_date'))
        if request.args.get('end_date'):
            end_date = datetime.fromisoformat(request.args.get('end_date'))
        
        filter_user_id = request.args.get('user_id')
        action_type = request.args.get('action_type')
        limit = int(request.args.get('limit', 100))
        
        db: Session = get_db_session()
        service = AdminService(db)
        
        logs = service.get_audit_logs(
            user_id,
            start_date=start_date,
            end_date=end_date,
            user_id=filter_user_id,
            action_type=action_type,
            limit=limit
        )
        
        return jsonify({'logs': logs}), 200
        
    except UnauthorizedAdminAccessError as e:
        logger.warning(f"Unauthorized admin access attempt: {e}")
        return jsonify({'error': 'Admin access required'}), 403
    except ValueError as e:
        logger.warning(f"Invalid parameter: {e}")
        return jsonify({'error': 'Invalid parameter format'}), 400
    except Exception as e:
        logger.error(f"Error getting audit logs: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        db.close()


@admin_bp.route('/reports/daily', methods=['GET'])
@require_auth
def get_daily_report():
    """
    Generate daily activity report.
    
    Query Parameters:
        date: Report date (ISO format, defaults to yesterday)
    
    Returns:
        JSON with daily report
    """
    try:
        user_id = request.user_id
        
        # Parse date
        report_date = None
        if request.args.get('date'):
            report_date = datetime.fromisoformat(request.args.get('date'))
        
        db: Session = get_db_session()
        service = AdminService(db)
        
        report = service.generate_daily_activity_report(user_id, report_date=report_date)
        
        return jsonify(report), 200
        
    except UnauthorizedAdminAccessError as e:
        logger.warning(f"Unauthorized admin access attempt: {e}")
        return jsonify({'error': 'Admin access required'}), 403
    except ValueError as e:
        logger.warning(f"Invalid date format: {e}")
        return jsonify({'error': 'Invalid date format. Use ISO format (YYYY-MM-DD)'}), 400
    except Exception as e:
        logger.error(f"Error generating daily report: {e}", exc_info=True)
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        db.close()
