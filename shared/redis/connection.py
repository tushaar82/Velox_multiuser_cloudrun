"""
Redis connection management with cluster support.
Provides connection pooling and automatic failover.
"""
import logging
from typing import Optional, Union, List, Any
import json

import redis
from redis import Redis, ConnectionPool
from redis.cluster import RedisCluster, ClusterNode
from redis.exceptions import RedisError, ConnectionError as RedisConnectionError

from shared.config import get_settings

logger = logging.getLogger(__name__)


class RedisManager:
    """Manages Redis connections with support for standalone and cluster modes."""
    
    def __init__(self):
        self.settings = get_settings()
        self._client: Optional[Union[Redis, RedisCluster]] = None
        self._pool: Optional[ConnectionPool] = None
    
    def initialize(self) -> None:
        """Initialize Redis client with appropriate configuration."""
        if self._client is not None:
            logger.warning("Redis already initialized")
            return
        
        try:
            if self.settings.redis_cluster_mode:
                self._initialize_cluster()
            else:
                self._initialize_standalone()
            
            # Test connection
            self._client.ping()
            logger.info("Redis connection established successfully")
            
        except RedisError as e:
            logger.error(f"Failed to initialize Redis: {e}")
            raise
    
    def _initialize_standalone(self) -> None:
        """Initialize standalone Redis connection."""
        self._pool = ConnectionPool(
            host=self.settings.redis_host,
            port=self.settings.redis_port,
            password=self.settings.redis_password,
            db=self.settings.redis_db,
            max_connections=self.settings.redis_max_connections,
            socket_timeout=self.settings.redis_socket_timeout,
            socket_connect_timeout=self.settings.redis_socket_connect_timeout,
            decode_responses=True,
            health_check_interval=30
        )
        
        self._client = Redis(connection_pool=self._pool)
        logger.info(
            f"Redis standalone initialized: {self.settings.redis_host}:{self.settings.redis_port}"
        )
    
    def _initialize_cluster(self) -> None:
        """Initialize Redis cluster connection."""
        if not self.settings.redis_cluster_nodes:
            raise ValueError("REDIS_CLUSTER_NODES must be set for cluster mode")
        
        # Parse cluster nodes (format: "host1:port1,host2:port2,...")
        nodes = []
        for node_str in self.settings.redis_cluster_nodes.split(','):
            host, port = node_str.strip().split(':')
            nodes.append(ClusterNode(host, int(port)))
        
        self._client = RedisCluster(
            startup_nodes=nodes,
            password=self.settings.redis_password,
            max_connections=self.settings.redis_max_connections,
            socket_timeout=self.settings.redis_socket_timeout,
            socket_connect_timeout=self.settings.redis_socket_connect_timeout,
            decode_responses=True,
            skip_full_coverage_check=True
        )
        
        logger.info(f"Redis cluster initialized with {len(nodes)} nodes")
    
    @property
    def client(self) -> Union[Redis, RedisCluster]:
        """Get Redis client."""
        if self._client is None:
            raise RuntimeError("Redis not initialized. Call initialize() first.")
        return self._client
    
    def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        try:
            return self.client.get(key)
        except RedisError as e:
            logger.error(f"Redis GET error for key '{key}': {e}")
            raise
    
    def set(
        self,
        key: str,
        value: str,
        ex: Optional[int] = None,
        px: Optional[int] = None,
        nx: bool = False,
        xx: bool = False
    ) -> bool:
        """
        Set key to value with optional expiration.
        
        Args:
            key: Key name
            value: Value to set
            ex: Expiration in seconds
            px: Expiration in milliseconds
            nx: Only set if key doesn't exist
            xx: Only set if key exists
        """
        try:
            return self.client.set(key, value, ex=ex, px=px, nx=nx, xx=xx)
        except RedisError as e:
            logger.error(f"Redis SET error for key '{key}': {e}")
            raise
    
    def delete(self, *keys: str) -> int:
        """Delete one or more keys."""
        try:
            return self.client.delete(*keys)
        except RedisError as e:
            logger.error(f"Redis DELETE error: {e}")
            raise
    
    def exists(self, *keys: str) -> int:
        """Check if keys exist."""
        try:
            return self.client.exists(*keys)
        except RedisError as e:
            logger.error(f"Redis EXISTS error: {e}")
            raise
    
    def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on key."""
        try:
            return self.client.expire(key, seconds)
        except RedisError as e:
            logger.error(f"Redis EXPIRE error for key '{key}': {e}")
            raise
    
    def hget(self, name: str, key: str) -> Optional[str]:
        """Get hash field value."""
        try:
            return self.client.hget(name, key)
        except RedisError as e:
            logger.error(f"Redis HGET error for hash '{name}', key '{key}': {e}")
            raise
    
    def hset(self, name: str, key: str, value: str) -> int:
        """Set hash field value."""
        try:
            return self.client.hset(name, key, value)
        except RedisError as e:
            logger.error(f"Redis HSET error for hash '{name}': {e}")
            raise
    
    def hgetall(self, name: str) -> dict:
        """Get all hash fields and values."""
        try:
            return self.client.hgetall(name)
        except RedisError as e:
            logger.error(f"Redis HGETALL error for hash '{name}': {e}")
            raise
    
    def hdel(self, name: str, *keys: str) -> int:
        """Delete hash fields."""
        try:
            return self.client.hdel(name, *keys)
        except RedisError as e:
            logger.error(f"Redis HDEL error for hash '{name}': {e}")
            raise
    
    def lpush(self, name: str, *values: str) -> int:
        """Push values to list head."""
        try:
            return self.client.lpush(name, *values)
        except RedisError as e:
            logger.error(f"Redis LPUSH error for list '{name}': {e}")
            raise
    
    def rpush(self, name: str, *values: str) -> int:
        """Push values to list tail."""
        try:
            return self.client.rpush(name, *values)
        except RedisError as e:
            logger.error(f"Redis RPUSH error for list '{name}': {e}")
            raise
    
    def lrange(self, name: str, start: int, end: int) -> List[str]:
        """Get list elements in range."""
        try:
            return self.client.lrange(name, start, end)
        except RedisError as e:
            logger.error(f"Redis LRANGE error for list '{name}': {e}")
            raise
    
    def publish(self, channel: str, message: str) -> int:
        """Publish message to channel."""
        try:
            return self.client.publish(channel, message)
        except RedisError as e:
            logger.error(f"Redis PUBLISH error for channel '{channel}': {e}")
            raise
    
    def subscribe(self, *channels: str):
        """Subscribe to channels."""
        try:
            pubsub = self.client.pubsub()
            pubsub.subscribe(*channels)
            return pubsub
        except RedisError as e:
            logger.error(f"Redis SUBSCRIBE error: {e}")
            raise
    
    def set_json(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        """Set JSON-serialized value."""
        try:
            json_value = json.dumps(value)
            return self.set(key, json_value, ex=ex)
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Redis SET_JSON error for key '{key}': {e}")
            raise
    
    def get_json(self, key: str) -> Optional[Any]:
        """Get and deserialize JSON value."""
        try:
            value = self.get(key)
            if value is None:
                return None
            return json.loads(value)
        except (RedisError, json.JSONDecodeError) as e:
            logger.error(f"Redis GET_JSON error for key '{key}': {e}")
            raise
    
    def ping(self) -> bool:
        """Test Redis connection."""
        try:
            return self.client.ping()
        except RedisError as e:
            logger.error(f"Redis PING error: {e}")
            return False
    
    def flushdb(self) -> bool:
        """Flush current database (use with caution!)."""
        try:
            return self.client.flushdb()
        except RedisError as e:
            logger.error(f"Redis FLUSHDB error: {e}")
            raise
    
    def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            self._client.close()
            logger.info("Redis connection closed")
            self._client = None
            self._pool = None
    
    def get_info(self) -> dict:
        """Get Redis server information."""
        try:
            return self.client.info()
        except RedisError as e:
            logger.error(f"Redis INFO error: {e}")
            raise


# Global Redis manager instance
_redis_manager: Optional[RedisManager] = None


def init_redis() -> RedisManager:
    """Initialize the global Redis manager."""
    global _redis_manager
    if _redis_manager is None:
        _redis_manager = RedisManager()
        _redis_manager.initialize()
    return _redis_manager


def get_redis_manager() -> RedisManager:
    """Get the global Redis manager instance."""
    if _redis_manager is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return _redis_manager


def get_redis_client() -> Union[Redis, RedisCluster]:
    """Get the Redis client instance."""
    return get_redis_manager().client
