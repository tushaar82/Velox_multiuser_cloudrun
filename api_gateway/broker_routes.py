"""API routes for broker connection management."""

import logging
from flask import Blueprint, request, jsonify
from functools import wraps

from api_gateway.broker_service import BrokerService
from api_gateway.middleware import require_auth, get_current_user
from shared.database.connection import get_db_session

logger = logging.getLogger(__name__)

broker_bp = Blueprint('broker', __name__, url_prefix='/api/broker')


def get_broker_service():
    """Get broker service instance."""
    db = get_db_session()
    return BrokerService(db)


@broker_bp.route('/connect', methods=['POST'])
@require_auth
def connect_broker():
    """
    Connect a broker account.
    
    Request body:
    {
        "broker_name": "angel_one",
        "credentials": {
            "api_key": "...",
            "client_code": "...",
            "password": "...",
            "totp_token": "..."
        }
    }
    
    Returns:
        Connection status
    """
    try:
        user = get_current_user()
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        broker_name = data.get('broker_name')
        credentials = data.get('credentials')
        
        if not broker_name or not credentials:
            return jsonify({'error': 'broker_name and credentials required'}), 400
        
        # Get user's account ID (assuming user has one account for now)
        # In production, this should be passed or derived from user context
        account_id = user.get('account_id')
        if not account_id:
            return jsonify({'error': 'User account not found'}), 400
        
        service = get_broker_service()
        result = service.connect_broker(account_id, broker_name, credentials)
        
        return jsonify(result), 200
        
    except ValueError as e:
        logger.warning(f"Invalid broker connection request: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except ConnectionError as e:
        logger.error(f"Broker connection failed: {str(e)}")
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        logger.error(f"Unexpected error in connect_broker: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@broker_bp.route('/disconnect', methods=['POST'])
@require_auth
def disconnect_broker():
    """
    Disconnect a broker account.
    
    Request body:
    {
        "broker_name": "angel_one"
    }
    
    Returns:
        Disconnection status
    """
    try:
        user = get_current_user()
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        broker_name = data.get('broker_name')
        
        if not broker_name:
            return jsonify({'error': 'broker_name required'}), 400
        
        account_id = user.get('account_id')
        if not account_id:
            return jsonify({'error': 'User account not found'}), 400
        
        service = get_broker_service()
        result = service.disconnect_broker(account_id, broker_name)
        
        return jsonify(result), 200
        
    except ValueError as e:
        logger.warning(f"Invalid disconnect request: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Unexpected error in disconnect_broker: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@broker_bp.route('/status/<broker_name>', methods=['GET'])
@require_auth
def get_broker_status(broker_name: str):
    """
    Get broker connection status.
    
    Args:
        broker_name: Name of broker
        
    Returns:
        Connection status
    """
    try:
        user = get_current_user()
        account_id = user.get('account_id')
        
        if not account_id:
            return jsonify({'error': 'User account not found'}), 400
        
        service = get_broker_service()
        result = service.get_connection_status(account_id, broker_name)
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Unexpected error in get_broker_status: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@broker_bp.route('/list', methods=['GET'])
@require_auth
def list_brokers():
    """
    List all available broker plugins.
    
    Returns:
        List of available brokers
    """
    try:
        service = get_broker_service()
        brokers = service.list_available_brokers()
        
        return jsonify({'brokers': brokers}), 200
        
    except Exception as e:
        logger.error(f"Unexpected error in list_brokers: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500


@broker_bp.route('/reconnect', methods=['POST'])
@require_auth
def reconnect_broker():
    """
    Reconnect a previously connected broker using stored credentials.
    
    Request body:
    {
        "broker_name": "angel_one"
    }
    
    Returns:
        Connection status
    """
    try:
        user = get_current_user()
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        broker_name = data.get('broker_name')
        
        if not broker_name:
            return jsonify({'error': 'broker_name required'}), 400
        
        account_id = user.get('account_id')
        if not account_id:
            return jsonify({'error': 'User account not found'}), 400
        
        service = get_broker_service()
        result = service.reconnect_broker(account_id, broker_name)
        
        return jsonify(result), 200
        
    except ValueError as e:
        logger.warning(f"Invalid reconnect request: {str(e)}")
        return jsonify({'error': str(e)}), 400
    except ConnectionError as e:
        logger.error(f"Broker reconnection failed: {str(e)}")
        return jsonify({'error': str(e)}), 500
    except Exception as e:
        logger.error(f"Unexpected error in reconnect_broker: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
