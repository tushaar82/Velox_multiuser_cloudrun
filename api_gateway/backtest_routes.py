"""
Backtest API Routes

Provides REST API endpoints for backtesting functionality.
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
import logging

from api_gateway.middleware import require_auth, require_role
from backtesting_engine.backtest_service import BacktestService
from shared.models.backtest import BacktestConfig
from shared.database.connection import get_db_session

logger = logging.getLogger(__name__)

backtest_bp = Blueprint('backtest', __name__, url_prefix='/api/backtest')
backtest_service = BacktestService()


@backtest_bp.route('/start', methods=['POST'])
@require_auth
@require_role(['trader', 'admin'])
def start_backtest():
    """
    Start a new backtest.
    
    Request body:
    {
        "strategy_id": "uuid",
        "symbols": ["RELIANCE", "TCS"],
        "timeframes": ["5m", "15m"],
        "start_date": "2024-01-01T00:00:00",
        "end_date": "2024-01-31T23:59:59",
        "initial_capital": 100000,
        "slippage": 0.0005,
        "commission": 0.0003,
        "strategy_params": {}
    }
    
    Returns:
    {
        "backtest_id": "uuid",
        "status": "running"
    }
    """
    try:
        data = request.get_json()
        user = request.user
        
        # Create backtest config
        config = BacktestConfig(
            strategy_id=data['strategy_id'],
            account_id=user['account_id'],
            symbols=data['symbols'],
            timeframes=data['timeframes'],
            start_date=datetime.fromisoformat(data['start_date']),
            end_date=datetime.fromisoformat(data['end_date']),
            initial_capital=float(data['initial_capital']),
            slippage=float(data.get('slippage', 0.0005)),
            commission=float(data.get('commission', 0.0003)),
            strategy_params=data.get('strategy_params', {})
        )
        
        # Start backtest
        db = next(get_db())
        try:
            backtest_id = backtest_service.start_backtest(config, db)
            
            return jsonify({
                'backtest_id': backtest_id,
                'status': 'running'
            }), 202
        finally:
            db.close()
    
    except ValueError as e:
        logger.warning(f"Invalid backtest request: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Failed to start backtest: {e}")
        return jsonify({'error': 'Failed to start backtest'}), 500


@backtest_bp.route('/<backtest_id>/status', methods=['GET'])
@require_auth
def get_backtest_status(backtest_id: str):
    """
    Get backtest status.
    
    Returns:
    {
        "id": "uuid",
        "status": "running|completed|failed",
        "created_at": "2024-01-01T00:00:00",
        "completed_at": "2024-01-01T01:00:00"
    }
    """
    try:
        db = next(get_db())
        try:
            status = backtest_service.get_backtest_status(backtest_id, db)
            
            if not status:
                return jsonify({'error': 'Backtest not found'}), 404
            
            return jsonify(status), 200
        finally:
            db.close()
    
    except Exception as e:
        logger.error(f"Failed to get backtest status: {e}")
        return jsonify({'error': 'Failed to get backtest status'}), 500


@backtest_bp.route('/<backtest_id>/results', methods=['GET'])
@require_auth
def get_backtest_results(backtest_id: str):
    """
    Get complete backtest results.
    
    Returns:
    {
        "id": "uuid",
        "config": {...},
        "metrics": {
            "total_return": 15.5,
            "annualized_return": 45.2,
            "max_drawdown": 8.3,
            "sharpe_ratio": 1.8,
            "sortino_ratio": 2.1,
            "win_rate": 65.0,
            "profit_factor": 1.9,
            "total_trades": 50,
            ...
        },
        "trades": [...],
        "equity_curve": [...],
        "completed_at": "2024-01-01T01:00:00"
    }
    """
    try:
        db = next(get_db())
        try:
            result = backtest_service.get_backtest_results(backtest_id, db)
            
            if not result:
                return jsonify({'error': 'Backtest not found or not completed'}), 404
            
            return jsonify(result.to_dict()), 200
        finally:
            db.close()
    
    except Exception as e:
        logger.error(f"Failed to get backtest results: {e}")
        return jsonify({'error': 'Failed to get backtest results'}), 500


@backtest_bp.route('/list', methods=['GET'])
@require_auth
def list_backtests():
    """
    List backtests for the user.
    
    Query parameters:
    - strategy_id: Filter by strategy ID (optional)
    - limit: Maximum number of results (default: 50)
    
    Returns:
    {
        "backtests": [
            {
                "id": "uuid",
                "strategy_id": "uuid",
                "status": "completed",
                "created_at": "2024-01-01T00:00:00",
                "completed_at": "2024-01-01T01:00:00",
                "summary": {
                    "total_return": 15.5,
                    "total_trades": 50,
                    "win_rate": 65.0,
                    "max_drawdown": 8.3
                }
            },
            ...
        ]
    }
    """
    try:
        user = request.user
        strategy_id = request.args.get('strategy_id')
        limit = int(request.args.get('limit', 50))
        
        db = next(get_db())
        try:
            backtests = backtest_service.list_backtests(
                strategy_id=strategy_id,
                account_id=user['account_id'],
                limit=limit,
                db=db
            )
            
            return jsonify({'backtests': backtests}), 200
        finally:
            db.close()
    
    except Exception as e:
        logger.error(f"Failed to list backtests: {e}")
        return jsonify({'error': 'Failed to list backtests'}), 500


@backtest_bp.route('/<backtest_id>/activate', methods=['POST'])
@require_auth
@require_role(['trader', 'admin'])
def activate_strategy(backtest_id: str):
    """
    Activate strategy in paper trading mode after successful backtest.
    
    Request body:
    {
        "trading_mode": "paper"
    }
    
    Returns:
    {
        "success": true,
        "message": "Strategy activated in paper trading mode",
        "strategy_id": "uuid",
        "trading_mode": "paper"
    }
    """
    try:
        data = request.get_json()
        trading_mode = data.get('trading_mode', 'paper')
        
        db = next(get_db())
        try:
            result = backtest_service.activate_strategy_from_backtest(
                backtest_id=backtest_id,
                trading_mode=trading_mode,
                db=db
            )
            
            return jsonify(result), 200
        finally:
            db.close()
    
    except ValueError as e:
        logger.warning(f"Invalid activation request: {e}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Failed to activate strategy: {e}")
        return jsonify({'error': 'Failed to activate strategy'}), 500
