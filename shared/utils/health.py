"""
Health check utilities for services.
"""
import logging
from typing import Dict, Any
from datetime import datetime
from flask import Blueprint, jsonify

from shared.database.connection import get_db_manager
from shared.redis.connection import get_redis_manager

logger = logging.getLogger(__name__)

# Create health check blueprint
health_bp = Blueprint('health', __name__, url_prefix='/health')


class HealthChecker:
    """Performs health checks on system components."""
    
    @staticmethod
    def check_database() -> Dict[str, Any]:
        """Check database connectivity and pool status."""
        try:
            db_manager = get_db_manager()
            
            # Test connection
            with db_manager.session_scope() as session:
                session.execute("SELECT 1")
            
            # Get pool status
            pool_status = db_manager.get_pool_status()
            
            return {
                "status": "healthy",
                "pool": pool_status,
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    @staticmethod
    def check_redis() -> Dict[str, Any]:
        """Check Redis connectivity."""
        try:
            redis_manager = get_redis_manager()
            
            # Test connection
            if not redis_manager.ping():
                raise Exception("Redis ping failed")
            
            # Get server info
            info = redis_manager.get_info()
            
            return {
                "status": "healthy",
                "version": info.get("redis_version"),
                "connected_clients": info.get("connected_clients"),
                "used_memory_human": info.get("used_memory_human"),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    @staticmethod
    def check_all() -> Dict[str, Any]:
        """Perform all health checks."""
        database = HealthChecker.check_database()
        redis = HealthChecker.check_redis()
        
        overall_status = "healthy"
        if database["status"] == "unhealthy" or redis["status"] == "unhealthy":
            overall_status = "unhealthy"
        
        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                "database": database,
                "redis": redis
            }
        }


# Health check routes
@health_bp.route('/', methods=['GET'])
@health_bp.route('', methods=['GET'])
def health_check():
    """Basic health check endpoint."""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    })


@health_bp.route('/detailed', methods=['GET'])
def detailed_health_check():
    """Detailed health check with all components."""
    result = HealthChecker.check_all()
    status_code = 200 if result["status"] == "healthy" else 503
    return jsonify(result), status_code
