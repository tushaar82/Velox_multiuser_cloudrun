"""
Analytics API Routes

This module defines the Flask routes for analytics endpoints.
"""

from flask import Blueprint, request, jsonify
from functools import wraps
from typing import Callable

from api_gateway.analytics_service import AnalyticsServiceLayer
from api_gateway.middleware import require_auth, get_current_user
from shared.database.connection import get_db_session
from shared.utils.logging_config import get_logger

logger = get_logger(__name__)

analytics_bp = Blueprint('analytics', __name__, url_prefix='/api/analytics')


def require_account_access(f: Callable) -> Callable:
    """Decorator to verify user has access to the account"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        account_id = request.view_args.get('account_id') or request.args.get('account_id')
        
        # TODO: Implement actual account access check
        # For now, just verify user is authenticated
        if not user:
            return jsonify({'error': 'Unauthorized'}), 401
        
        return f(*args, **kwargs)
    return decorated_function


@analytics_bp.route('/performance/<account_id>', methods=['GET'])
@require_auth
@require_account_access
def get_performance_metrics(account_id: str):
    """
    Get performance metrics for specified period and trading mode
    
    Query Parameters:
        - trading_mode: 'paper' or 'live' (required)
        - period: 'daily', 'weekly', 'monthly', 'yearly', 'all', 'custom' (required)
        - start_date: ISO format date (required for custom period)
        - end_date: ISO format date (required for custom period)
    
    Returns:
        JSON with performance metrics
    """
    try:
        trading_mode = request.args.get('trading_mode')
        period_type = request.args.get('period')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not trading_mode or not period_type:
            return jsonify({'error': 'trading_mode and period are required'}), 400
        
        if trading_mode not in ['paper', 'live']:
            return jsonify({'error': 'trading_mode must be paper or live'}), 400
        
        db = get_db_session()
        service = AnalyticsServiceLayer(db)
        
        result = service.get_performance_metrics(
            account_id=account_id,
            trading_mode=trading_mode,
            period_type=period_type,
            start_date=start_date,
            end_date=end_date
        )
        
        return jsonify(result), 200
        
    except ValueError as e:
        logger.error(f"Validation error in get_performance_metrics: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error in get_performance_metrics: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@analytics_bp.route('/equity-curve/<account_id>', methods=['GET'])
@require_auth
@require_account_access
def get_equity_curve(account_id: str):
    """
    Get equity curve data
    
    Query Parameters:
        - trading_mode: 'paper' or 'live' (required)
        - start_date: ISO format date (required)
        - end_date: ISO format date (required)
    
    Returns:
        JSON with equity curve data points
    """
    try:
        trading_mode = request.args.get('trading_mode')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not all([trading_mode, start_date, end_date]):
            return jsonify({'error': 'trading_mode, start_date, and end_date are required'}), 400
        
        if trading_mode not in ['paper', 'live']:
            return jsonify({'error': 'trading_mode must be paper or live'}), 400
        
        db = get_db_session()
        service = AnalyticsServiceLayer(db)
        
        result = service.get_equity_curve(
            account_id=account_id,
            trading_mode=trading_mode,
            start_date=start_date,
            end_date=end_date
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error in get_equity_curve: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@analytics_bp.route('/strategy-breakdown/<account_id>', methods=['GET'])
@require_auth
@require_account_access
def get_strategy_breakdown(account_id: str):
    """
    Get strategy-level performance breakdown
    
    Query Parameters:
        - trading_mode: 'paper' or 'live' (required)
        - period: 'daily', 'weekly', 'monthly', 'yearly', 'all', 'custom' (required)
        - start_date: ISO format date (required for custom period)
        - end_date: ISO format date (required for custom period)
    
    Returns:
        JSON with strategy breakdown
    """
    try:
        trading_mode = request.args.get('trading_mode')
        period_type = request.args.get('period')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not trading_mode or not period_type:
            return jsonify({'error': 'trading_mode and period are required'}), 400
        
        if trading_mode not in ['paper', 'live']:
            return jsonify({'error': 'trading_mode must be paper or live'}), 400
        
        db = get_db_session()
        service = AnalyticsServiceLayer(db)
        
        result = service.get_strategy_breakdown(
            account_id=account_id,
            trading_mode=trading_mode,
            period_type=period_type,
            start_date=start_date,
            end_date=end_date
        )
        
        return jsonify(result), 200
        
    except ValueError as e:
        logger.error(f"Validation error in get_strategy_breakdown: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error in get_strategy_breakdown: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@analytics_bp.route('/trade-analysis/<account_id>', methods=['GET'])
@require_auth
@require_account_access
def get_trade_analysis(account_id: str):
    """
    Get detailed trade analysis
    
    Query Parameters:
        - trading_mode: 'paper' or 'live' (required)
        - period: 'daily', 'weekly', 'monthly', 'yearly', 'all', 'custom' (required)
        - start_date: ISO format date (required for custom period)
        - end_date: ISO format date (required for custom period)
    
    Returns:
        JSON with trade analysis
    """
    try:
        trading_mode = request.args.get('trading_mode')
        period_type = request.args.get('period')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not trading_mode or not period_type:
            return jsonify({'error': 'trading_mode and period are required'}), 400
        
        if trading_mode not in ['paper', 'live']:
            return jsonify({'error': 'trading_mode must be paper or live'}), 400
        
        db = get_db_session()
        service = AnalyticsServiceLayer(db)
        
        result = service.get_trade_analysis(
            account_id=account_id,
            trading_mode=trading_mode,
            period_type=period_type,
            start_date=start_date,
            end_date=end_date
        )
        
        return jsonify(result), 200
        
    except ValueError as e:
        logger.error(f"Validation error in get_trade_analysis: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error in get_trade_analysis: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@analytics_bp.route('/benchmark-comparison/<account_id>', methods=['GET'])
@require_auth
@require_account_access
def compare_to_benchmark(account_id: str):
    """
    Compare performance to benchmark index
    
    Query Parameters:
        - trading_mode: 'paper' or 'live' (required)
        - benchmark: Benchmark name (e.g., 'NIFTY 50', 'BANK NIFTY') (required)
        - period: 'daily', 'weekly', 'monthly', 'yearly', 'all', 'custom' (required)
        - start_date: ISO format date (required for custom period)
        - end_date: ISO format date (required for custom period)
    
    Returns:
        JSON with benchmark comparison metrics
    """
    try:
        trading_mode = request.args.get('trading_mode')
        benchmark_name = request.args.get('benchmark')
        period_type = request.args.get('period')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not all([trading_mode, benchmark_name, period_type]):
            return jsonify({'error': 'trading_mode, benchmark, and period are required'}), 400
        
        if trading_mode not in ['paper', 'live']:
            return jsonify({'error': 'trading_mode must be paper or live'}), 400
        
        db = get_db_session()
        service = AnalyticsServiceLayer(db)
        
        result = service.compare_to_benchmark(
            account_id=account_id,
            trading_mode=trading_mode,
            benchmark_name=benchmark_name,
            period_type=period_type,
            start_date=start_date,
            end_date=end_date
        )
        
        return jsonify(result), 200
        
    except ValueError as e:
        logger.error(f"Validation error in compare_to_benchmark: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error in compare_to_benchmark: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@analytics_bp.route('/export/<account_id>', methods=['GET'])
@require_auth
@require_account_access
def export_report(account_id: str):
    """
    Export analytics report in specified format
    
    Query Parameters:
        - trading_mode: 'paper' or 'live' (required)
        - format: 'pdf' or 'csv' (required)
        - period: 'daily', 'weekly', 'monthly', 'yearly', 'all', 'custom' (required)
        - benchmark: Benchmark name (optional)
        - start_date: ISO format date (required for custom period)
        - end_date: ISO format date (required for custom period)
    
    Returns:
        File download (PDF or CSV)
    """
    try:
        trading_mode = request.args.get('trading_mode')
        format_type = request.args.get('format')
        period_type = request.args.get('period')
        benchmark_name = request.args.get('benchmark')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not all([trading_mode, format_type, period_type]):
            return jsonify({'error': 'trading_mode, format, and period are required'}), 400
        
        if trading_mode not in ['paper', 'live']:
            return jsonify({'error': 'trading_mode must be paper or live'}), 400
        
        if format_type not in ['pdf', 'csv']:
            return jsonify({'error': 'format must be pdf or csv'}), 400
        
        db = get_db_session()
        service = AnalyticsServiceLayer(db)
        
        return service.export_report(
            account_id=account_id,
            trading_mode=trading_mode,
            format=format_type,
            period_type=period_type,
            benchmark_name=benchmark_name,
            start_date=start_date,
            end_date=end_date
        )
        
    except ValueError as e:
        logger.error(f"Validation error in export_report: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error in export_report: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


def register_analytics_routes(app):
    """Register analytics blueprint with Flask app"""
    app.register_blueprint(analytics_bp)
    logger.info("Analytics routes registered")
