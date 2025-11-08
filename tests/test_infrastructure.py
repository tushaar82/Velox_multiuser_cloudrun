"""
Test infrastructure setup and configuration.
"""
import pytest
from shared.config import get_settings


def test_settings_load():
    """Test that settings can be loaded."""
    settings = get_settings()
    assert settings is not None
    assert settings.app_name == "Trading Platform"
    assert settings.environment in ["development", "production", "staging"]


def test_database_url_construction():
    """Test database URL construction."""
    settings = get_settings()
    db_url = settings.database_url
    assert db_url.startswith("postgresql://")
    assert settings.db_name in db_url


def test_redis_url_construction():
    """Test Redis URL construction."""
    settings = get_settings()
    redis_url = settings.redis_url
    assert redis_url.startswith("redis://")


def test_jwt_configuration():
    """Test JWT configuration."""
    settings = get_settings()
    assert settings.jwt_secret_key is not None
    assert settings.jwt_algorithm == "HS256"
    assert settings.jwt_expiration_hours > 0


def test_security_settings():
    """Test security settings."""
    settings = get_settings()
    assert settings.password_min_length >= 8
    assert settings.max_login_attempts > 0
    assert settings.account_lock_duration_minutes > 0
    assert settings.session_timeout_minutes > 0


def test_pool_configuration():
    """Test database pool configuration."""
    settings = get_settings()
    assert settings.db_pool_size > 0
    assert settings.db_max_overflow >= 0
    assert settings.db_pool_timeout > 0
    assert settings.db_pool_recycle > 0


def test_redis_configuration():
    """Test Redis configuration."""
    settings = get_settings()
    assert settings.redis_max_connections > 0
    assert settings.redis_socket_timeout > 0
    assert settings.redis_socket_connect_timeout > 0
