"""
WebSocket Service - Real-time updates and bidirectional communication.
"""
from websocket_service.websocket_server import (
    socketio,
    app,
    broadcast_to_room,
    broadcast_to_user,
    publish_broadcast,
    get_active_connections_count,
    get_active_users_count,
    get_room_subscribers_count
)
from websocket_service.room_manager import RoomManager

__all__ = [
    'socketio',
    'app',
    'broadcast_to_room',
    'broadcast_to_user',
    'publish_broadcast',
    'get_active_connections_count',
    'get_active_users_count',
    'get_room_subscribers_count',
    'RoomManager'
]
