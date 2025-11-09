"""
Replay API Endpoints

Provides REST API for controlling replay sessions.
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from typing import Optional
import logging

from .simulator import MarketDataSimulator, SimulatorController
from .replay_manager import ReplaySessionManager

logger = logging.getLogger(__name__)

# Create blueprint
replay_bp = Blueprint('replay', __name__, url_prefix='/api/replay')

# Global instances
simulator = MarketDataSimulator()
controller = SimulatorController(simulator)
session_manager = ReplaySessionManager()
session_manager.attach_simulator(simulator)


@replay_bp.route('/sessions', methods=['GET'])
def list_sessions():
    """List all replay sessions"""
    try:
        sessions = session_manager.list_sessions()
        return jsonify({
            'success': True,
            'sessions': sessions
        })
    except Exception as e:
        logger.error(f"Error listing sessions: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@replay_bp.route('/sessions', methods=['POST'])
def create_session():
    """Create a new replay session"""
    try:
        data = request.json
        
        session_id = session_manager.create_session(
            name=data['name'],
            symbols=data['symbols'],
            start_time=datetime.fromisoformat(data['start_time']),
            end_time=datetime.fromisoformat(data['end_time']),
            strategy_configs=data.get('strategy_configs')
        )
        
        return jsonify({
            'success': True,
            'session_id': session_id
        })
    except Exception as e:
        logger.error(f"Error creating session: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@replay_bp.route('/sessions/<session_id>', methods=['GET'])
def get_session(session_id: str):
    """Get session details"""
    try:
        session = session_manager.load_session(session_id)
        
        return jsonify({
            'success': True,
            'session': {
                'session_id': session.session_id,
                'name': session.name,
                'created_at': session.created_at.isoformat(),
                'symbols': session.symbols,
                'start_time': session.start_time.isoformat(),
                'end_time': session.end_time.isoformat(),
                'current_time': session.current_time.isoformat() if session.current_time else None,
                'speed': session.speed,
                'state': session.state,
                'num_events': len(session.events),
                'performance_metrics': session.performance_metrics
            }
        })
    except Exception as e:
        logger.error(f"Error getting session: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@replay_bp.route('/sessions/<session_id>', methods=['DELETE'])
def delete_session(session_id: str):
    """Delete a replay session"""
    try:
        success = session_manager.delete_session(session_id)
        
        return jsonify({
            'success': success
        })
    except Exception as e:
        logger.error(f"Error deleting session: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@replay_bp.route('/sessions/<session_id>/save', methods=['POST'])
def save_session(session_id: str):
    """Save current session state"""
    try:
        file_path = session_manager.save_session(session_id)
        
        return jsonify({
            'success': True,
            'file_path': file_path
        })
    except Exception as e:
        logger.error(f"Error saving session: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@replay_bp.route('/sessions/<session_id>/load', methods=['POST'])
def load_session(session_id: str):
    """Load a saved session"""
    try:
        session = session_manager.load_session(session_id)
        
        return jsonify({
            'success': True,
            'session_id': session.session_id
        })
    except Exception as e:
        logger.error(f"Error loading session: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@replay_bp.route('/control/start', methods=['POST'])
def start_replay():
    """Start replay"""
    try:
        data = request.json or {}
        symbols = data.get('symbols')
        
        result = controller.start(symbols)
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error starting replay: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@replay_bp.route('/control/pause', methods=['POST'])
def pause_replay():
    """Pause replay"""
    try:
        result = controller.pause()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error pausing replay: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@replay_bp.route('/control/resume', methods=['POST'])
def resume_replay():
    """Resume replay"""
    try:
        result = controller.resume()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error resuming replay: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@replay_bp.route('/control/stop', methods=['POST'])
def stop_replay():
    """Stop replay"""
    try:
        result = controller.stop()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error stopping replay: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@replay_bp.route('/control/speed', methods=['POST'])
def set_speed():
    """Set replay speed"""
    try:
        data = request.json
        speed = data.get('speed', 1.0)
        
        result = controller.set_speed(speed)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error setting speed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@replay_bp.route('/control/jump', methods=['POST'])
def jump_to_time():
    """Jump to specific time"""
    try:
        data = request.json
        timestamp = data.get('timestamp')
        
        if not timestamp:
            return jsonify({
                'success': False,
                'error': 'timestamp required'
            }), 400
        
        result = controller.jump_to_time(timestamp)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error jumping to time: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@replay_bp.route('/control/status', methods=['GET'])
def get_status():
    """Get replay status"""
    try:
        result = controller.get_status()
        return jsonify({
            'success': True,
            'status': result
        })
    except Exception as e:
        logger.error(f"Error getting status: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@replay_bp.route('/data/load', methods=['POST'])
def load_data():
    """Load data from CSV"""
    try:
        data = request.json
        symbol = data.get('symbol')
        csv_file = data.get('csv_file')
        
        if not symbol or not csv_file:
            return jsonify({
                'success': False,
                'error': 'symbol and csv_file required'
            }), 400
        
        result = controller.load_data(symbol, csv_file)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error loading data: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@replay_bp.route('/data/generate', methods=['POST'])
def generate_data():
    """Generate synthetic data"""
    try:
        data = request.json
        
        result = controller.generate_data(
            symbol=data['symbol'],
            start_price=data['start_price'],
            num_ticks=data['num_ticks'],
            volatility=data.get('volatility', 0.02),
            trend=data.get('trend', 0.0)
        )
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error generating data: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@replay_bp.route('/events', methods=['GET'])
def get_events():
    """Get replay events"""
    try:
        event_type = request.args.get('event_type')
        symbol = request.args.get('symbol')
        start_time = request.args.get('start_time')
        end_time = request.args.get('end_time')
        
        # Convert timestamps
        start_dt = datetime.fromisoformat(start_time) if start_time else None
        end_dt = datetime.fromisoformat(end_time) if end_time else None
        
        events = session_manager.get_events(
            event_type=event_type,
            symbol=symbol,
            start_time=start_dt,
            end_time=end_dt
        )
        
        return jsonify({
            'success': True,
            'events': [
                {
                    'timestamp': e.timestamp.isoformat(),
                    'event_type': e.event_type,
                    'symbol': e.symbol,
                    'data': e.data
                }
                for e in events
            ]
        })
    except Exception as e:
        logger.error(f"Error getting events: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@replay_bp.route('/compare', methods=['POST'])
def compare_sessions():
    """Compare multiple replay sessions"""
    try:
        data = request.json
        session_ids = data.get('session_ids', [])
        
        if not session_ids:
            return jsonify({
                'success': False,
                'error': 'session_ids required'
            }), 400
        
        comparison = session_manager.compare_sessions(session_ids)
        
        return jsonify({
            'success': True,
            'comparison': comparison
        })
    except Exception as e:
        logger.error(f"Error comparing sessions: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
