"""
Development Mode API

Provides API endpoints for development mode features.
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
from typing import Optional
import logging

from .strategy_debugger import (
    StrategyDebugger,
    VariableInspector,
    BreakpointType
)

logger = logging.getLogger(__name__)

# Create blueprint
dev_mode_bp = Blueprint('dev_mode', __name__, url_prefix='/api/dev')

# Global instances
debugger = StrategyDebugger()
inspector = VariableInspector()

# Connect inspector to debugger
debugger.on_frame_captured(inspector.update)


@dev_mode_bp.route('/debugger/breakpoints', methods=['GET'])
def list_breakpoints():
    """List all breakpoints"""
    try:
        breakpoints = debugger.get_breakpoints()
        return jsonify({
            'success': True,
            'breakpoints': breakpoints
        })
    except Exception as e:
        logger.error(f"Error listing breakpoints: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dev_mode_bp.route('/debugger/breakpoints', methods=['POST'])
def add_breakpoint():
    """Add a breakpoint"""
    try:
        data = request.json
        
        breakpoint_type = BreakpointType(data['type'])
        condition = data.get('condition')
        max_hits = data.get('max_hits')
        
        breakpoint_id = debugger.add_breakpoint(
            breakpoint_type=breakpoint_type,
            condition=condition,
            max_hits=max_hits
        )
        
        return jsonify({
            'success': True,
            'breakpoint_id': breakpoint_id
        })
    except Exception as e:
        logger.error(f"Error adding breakpoint: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dev_mode_bp.route('/debugger/breakpoints/<breakpoint_id>', methods=['DELETE'])
def remove_breakpoint(breakpoint_id: str):
    """Remove a breakpoint"""
    try:
        success = debugger.remove_breakpoint(breakpoint_id)
        return jsonify({
            'success': success
        })
    except Exception as e:
        logger.error(f"Error removing breakpoint: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dev_mode_bp.route('/debugger/breakpoints/<breakpoint_id>/enable', methods=['POST'])
def enable_breakpoint(breakpoint_id: str):
    """Enable a breakpoint"""
    try:
        success = debugger.enable_breakpoint(breakpoint_id)
        return jsonify({
            'success': success
        })
    except Exception as e:
        logger.error(f"Error enabling breakpoint: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dev_mode_bp.route('/debugger/breakpoints/<breakpoint_id>/disable', methods='POST'])
def disable_breakpoint(breakpoint_id: str):
    """Disable a breakpoint"""
    try:
        success = debugger.disable_breakpoint(breakpoint_id)
        return jsonify({
            'success': success
        })
    except Exception as e:
        logger.error(f"Error disabling breakpoint: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dev_mode_bp.route('/debugger/pause', methods=['POST'])
def pause_debugger():
    """Pause debugger"""
    try:
        debugger.pause()
        return jsonify({
            'success': True
        })
    except Exception as e:
        logger.error(f"Error pausing debugger: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dev_mode_bp.route('/debugger/resume', methods=['POST'])
def resume_debugger():
    """Resume debugger"""
    try:
        debugger.resume()
        return jsonify({
            'success': True
        })
    except Exception as e:
        logger.error(f"Error resuming debugger: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dev_mode_bp.route('/debugger/step', methods=['POST'])
def step_debugger():
    """Step to next event"""
    try:
        debugger.step()
        return jsonify({
            'success': True
        })
    except Exception as e:
        logger.error(f"Error stepping debugger: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dev_mode_bp.route('/debugger/state', methods=['GET'])
def get_debugger_state():
    """Get debugger state"""
    try:
        state = debugger.get_state()
        return jsonify({
            'success': True,
            'state': state
        })
    except Exception as e:
        logger.error(f"Error getting debugger state: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dev_mode_bp.route('/debugger/frames', methods=['GET'])
def get_frames():
    """Get debug frames"""
    try:
        limit = int(request.args.get('limit', 100))
        frames = debugger.get_frames(limit=limit)
        
        return jsonify({
            'success': True,
            'frames': [
                {
                    'timestamp': f.timestamp.isoformat(),
                    'symbol': f.symbol,
                    'timeframe': f.timeframe,
                    'candle_data': f.candle_data,
                    'indicator_values': f.indicator_values,
                    'strategy_variables': f.strategy_variables,
                    'signals': f.signals,
                    'positions': f.positions,
                    'orders': f.orders
                }
                for f in frames
            ]
        })
    except Exception as e:
        logger.error(f"Error getting frames: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dev_mode_bp.route('/debugger/frames/current', methods=['GET'])
def get_current_frame():
    """Get current debug frame"""
    try:
        frame = debugger.get_current_frame()
        
        if frame is None:
            return jsonify({
                'success': True,
                'frame': None
            })
        
        return jsonify({
            'success': True,
            'frame': {
                'timestamp': frame.timestamp.isoformat(),
                'symbol': frame.symbol,
                'timeframe': frame.timeframe,
                'candle_data': frame.candle_data,
                'indicator_values': frame.indicator_values,
                'strategy_variables': frame.strategy_variables,
                'signals': frame.signals,
                'positions': frame.positions,
                'orders': frame.orders
            }
        })
    except Exception as e:
        logger.error(f"Error getting current frame: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dev_mode_bp.route('/inspector/watch/variable', methods=['POST'])
def watch_variable():
    """Watch a variable"""
    try:
        data = request.json
        name = data.get('name')
        
        if not name:
            return jsonify({
                'success': False,
                'error': 'name required'
            }), 400
        
        inspector.watch_variable(name)
        return jsonify({
            'success': True
        })
    except Exception as e:
        logger.error(f"Error watching variable: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dev_mode_bp.route('/inspector/watch/indicator', methods=['POST'])
def watch_indicator():
    """Watch an indicator"""
    try:
        data = request.json
        name = data.get('name')
        
        if not name:
            return jsonify({
                'success': False,
                'error': 'name required'
            }), 400
        
        inspector.watch_indicator(name)
        return jsonify({
            'success': True
        })
    except Exception as e:
        logger.error(f"Error watching indicator: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dev_mode_bp.route('/inspector/unwatch/variable/<name>', methods=['DELETE'])
def unwatch_variable(name: str):
    """Stop watching a variable"""
    try:
        inspector.unwatch_variable(name)
        return jsonify({
            'success': True
        })
    except Exception as e:
        logger.error(f"Error unwatching variable: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dev_mode_bp.route('/inspector/unwatch/indicator/<name>', methods=['DELETE'])
def unwatch_indicator(name: str):
    """Stop watching an indicator"""
    try:
        inspector.unwatch_indicator(name)
        return jsonify({
            'success': True
        })
    except Exception as e:
        logger.error(f"Error unwatching indicator: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dev_mode_bp.route('/inspector/values', methods=['GET'])
def get_current_values():
    """Get current values of watched items"""
    try:
        values = inspector.get_current_values()
        return jsonify({
            'success': True,
            'values': values
        })
    except Exception as e:
        logger.error(f"Error getting current values: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dev_mode_bp.route('/inspector/history/variable/<name>', methods=['GET'])
def get_variable_history(name: str):
    """Get variable history"""
    try:
        limit = int(request.args.get('limit', 100))
        history = inspector.get_variable_history(name, limit=limit)
        
        return jsonify({
            'success': True,
            'history': history
        })
    except Exception as e:
        logger.error(f"Error getting variable history: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@dev_mode_bp.route('/inspector/history/indicator/<name>', methods=['GET'])
def get_indicator_history(name: str):
    """Get indicator history"""
    try:
        limit = int(request.args.get('limit', 100))
        history = inspector.get_indicator_history(name, limit=limit)
        
        return jsonify({
            'success': True,
            'history': history
        })
    except Exception as e:
        logger.error(f"Error getting indicator history: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
