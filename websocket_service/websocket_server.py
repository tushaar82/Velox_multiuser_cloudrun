"""
WebSocket Server - Real-time bidirectional communication.
Implements Flask-SocketIO server with JWT authentication and Redis pub/sub.
"""
import logging
from typing import Dict, Set, Optional, Any
from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room, leave_room, disconnect
from flask_cors import CORS
import redis
import json
from functools import wraps

from shared.utils.jwt import decode_token
from shared.config import get_settings

logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Get settings
settings = get_settings()

# Initialize SocketIO with Redis adapter for multi-instance support
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='threading',
    message_queue=f'redis://{settings.redis_host}:{settings.redis_port}/0',
    logger=True,
    engineio_logger=True
)

# Initialize Redis client for pub/sub
redis_client = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    db=0,
    decode_responses=True
)

# Track active connections and subscriptions
# Format: {user_id: {sid1, sid2, ...}}
user_connections: Dict[str, Set[str]] = {}

# Format: {room_name: {sid1, sid2, ...}}
room_subscriptions: Dict[str, Set[str]] = {}


def authenticated_only(f):
    """
    Decorator to require authentication for WebSocket events.
    Validates JWT token from connection query parameters or headers.
    """
    @wraps(f)
    def wrapped(*args, **kwargs):
        # Get token from query parameters or headers
        token = request.args.get('token') or request.headers.get('Authorization')
        
        if token and token.startswith('Bearer '):
            token = token[7:]  # Remove 'Bearer ' prefix
        
        if not token:
            logger.warning(f"WebSocket connection attempt without token from {request.sid}")
            disconnect()
            return
        
        # Decode and validate token
        payload = decode_token(token)
        if not payload:
            logger.warning(f"WebSocket connection attempt with invalid token from {request.sid}")
            disconnect()
            return
        
        # Store user info in session
        request.user_id = payload.get('user_id')
        request.user_role = payload.get('role')
        
        return f(*args, **kwargs)
    
    return wrapped


@socketio.on('connect')
@authenticated_only
def handle_connect():
    """Handle new WebSocket connection."""
    user_id = request.user_id
    sid = request.sid
    
    # Track connection
    if user_id not in user_connections:
        user_connections[user_id] = set()
    user_connections[user_id].add(sid)
    
    logger.info(f"User {user_id} connected with session {sid}")
    
    emit('connected', {
        'status': 'success',
        'message': 'Connected to WebSocket server',
        'user_id': user_id
    })


@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection."""
    sid = request.sid
    user_id = getattr(request, 'user_id', None)
    
    if user_id:
        # Remove from user connections
        if user_id in user_connections:
            user_connections[user_id].discard(sid)
            if not user_connections[user_id]:
                del user_connections[user_id]
        
        # Remove from all room subscriptions
        rooms_to_remove = []
        for room_name, sids in room_subscriptions.items():
            if sid in sids:
                sids.discard(sid)
                if not sids:
                    rooms_to_remove.append(room_name)
        
        for room_name in rooms_to_remove:
            del room_subscriptions[room_name]
        
        logger.info(f"User {user_id} disconnected session {sid}")
    else:
        logger.info(f"Anonymous session {sid} disconnected")


@socketio.on('ping')
@authenticated_only
def handle_ping():
    """Handle ping for connection keep-alive."""
    emit('pong', {'timestamp': str(datetime.utcnow())})


def subscribe_to_room(room_name: str):
    """
    Subscribe current connection to a room.
    
    Args:
        room_name: Name of the room to join
    """
    sid = request.sid
    join_room(room_name)
    
    if room_name not in room_subscriptions:
        room_subscriptions[room_name] = set()
    room_subscriptions[room_name].add(sid)
    
    logger.debug(f"Session {sid} subscribed to room {room_name}")


def unsubscribe_from_room(room_name: str):
    """
    Unsubscribe current connection from a room.
    
    Args:
        room_name: Name of the room to leave
    """
    sid = request.sid
    leave_room(room_name)
    
    if room_name in room_subscriptions:
        room_subscriptions[room_name].discard(sid)
        if not room_subscriptions[room_name]:
            del room_subscriptions[room_name]
    
    logger.debug(f"Session {sid} unsubscribed from room {room_name}")


def broadcast_to_room(room_name: str, event: str, data: Dict[str, Any]):
    """
    Broadcast message to all clients in a room.
    
    Args:
        room_name: Name of the room
        event: Event name
        data: Data to broadcast
    """
    socketio.emit(event, data, room=room_name)
    logger.debug(f"Broadcasted {event} to room {room_name}")


def broadcast_to_user(user_id: str, event: str, data: Dict[str, Any]):
    """
    Broadcast message to all connections of a specific user.
    
    Args:
        user_id: User ID
        event: Event name
        data: Data to broadcast
    """
    if user_id in user_connections:
        for sid in user_connections[user_id]:
            socketio.emit(event, data, room=sid)
        logger.debug(f"Broadcasted {event} to user {user_id}")


def start_redis_listener():
    """
    Start Redis pub/sub listener for cross-instance broadcasting.
    Runs in a separate thread to listen for messages from other instances.
    """
    pubsub = redis_client.pubsub()
    pubsub.subscribe('websocket_broadcast')
    
    logger.info("Started Redis pub/sub listener for WebSocket broadcasting")
    
    for message in pubsub.listen():
        if message['type'] == 'message':
            try:
                data = json.loads(message['data'])
                event = data.get('event')
                payload = data.get('payload')
                room = data.get('room')
                user_id = data.get('user_id')
                
                if room:
                    broadcast_to_room(room, event, payload)
                elif user_id:
                    broadcast_to_user(user_id, event, payload)
                else:
                    # Broadcast to all connected clients
                    socketio.emit(event, payload)
                    
            except Exception as e:
                logger.error(f"Error processing Redis pub/sub message: {e}")


def publish_broadcast(event: str, payload: Dict[str, Any], 
                     room: Optional[str] = None, 
                     user_id: Optional[str] = None):
    """
    Publish a broadcast message via Redis pub/sub for cross-instance delivery.
    
    Args:
        event: Event name
        payload: Data to broadcast
        room: Optional room name to broadcast to
        user_id: Optional user ID to broadcast to
    """
    message = {
        'event': event,
        'payload': payload,
        'room': room,
        'user_id': user_id
    }
    
    redis_client.publish('websocket_broadcast', json.dumps(message))
    logger.debug(f"Published broadcast message: {event}")


def get_active_connections_count() -> int:
    """Get total number of active WebSocket connections."""
    return sum(len(sids) for sids in user_connections.values())


def get_active_users_count() -> int:
    """Get number of unique users with active connections."""
    return len(user_connections)


def get_room_subscribers_count(room_name: str) -> int:
    """Get number of subscribers in a specific room."""
    return len(room_subscriptions.get(room_name, set()))


# Import datetime for ping handler
from datetime import datetime


if __name__ == '__main__':
    # Start Redis listener in background thread
    import threading
    listener_thread = threading.Thread(target=start_redis_listener, daemon=True)
    listener_thread.start()
    
    # Start WebSocket server
    logger.info("Starting WebSocket server...")
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)
