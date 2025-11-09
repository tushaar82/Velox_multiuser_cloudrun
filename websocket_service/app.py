"""
WebSocket Service Entry Point

Main application for WebSocket real-time communication.
"""
import logging
from shared.utils.logging_config import setup_logging
from shared.config.settings import get_settings
from websocket_service.websocket_server import app, socketio

# Setup logging
setup_logging('websocket_service')
logger = logging.getLogger(__name__)

# Get settings
settings = get_settings()

logger.info("WebSocket service initialized")

if __name__ == '__main__':
    port = int(settings.websocket_port) if hasattr(settings, 'websocket_port') else 8081
    socketio.run(app, host='0.0.0.0', port=port, debug=False, allow_unsafe_werkzeug=True)
