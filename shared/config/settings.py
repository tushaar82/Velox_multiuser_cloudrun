"""
Configuration management for the trading platform.
Handles environment variables and secrets.
"""
from functools import lru_cache
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Application
    app_name: str = Field(default="Trading Platform", alias="APP_NAME")
    environment: str = Field(default="development", alias="ENVIRONMENT")
    debug: bool = Field(default=False, alias="DEBUG")
    
    # Database Configuration
    db_host: str = Field(default="localhost", alias="DB_HOST")
    db_port: int = Field(default=5432, alias="DB_PORT")
    db_name: str = Field(default="trading_platform", alias="DB_NAME")
    db_user: str = Field(default="postgres", alias="DB_USER")
    db_password: str = Field(default="postgres", alias="DB_PASSWORD")
    db_pool_size: int = Field(default=20, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=10, alias="DB_MAX_OVERFLOW")
    db_pool_timeout: int = Field(default=30, alias="DB_POOL_TIMEOUT")
    db_pool_recycle: int = Field(default=3600, alias="DB_POOL_RECYCLE")
    
    # PgBouncer Configuration
    use_pgbouncer: bool = Field(default=False, alias="USE_PGBOUNCER")
    pgbouncer_host: Optional[str] = Field(default=None, alias="PGBOUNCER_HOST")
    pgbouncer_port: int = Field(default=6432, alias="PGBOUNCER_PORT")
    
    # Redis Configuration
    redis_host: str = Field(default="localhost", alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_password: Optional[str] = Field(default=None, alias="REDIS_PASSWORD")
    redis_db: int = Field(default=0, alias="REDIS_DB")
    redis_cluster_mode: bool = Field(default=False, alias="REDIS_CLUSTER_MODE")
    redis_cluster_nodes: Optional[str] = Field(default=None, alias="REDIS_CLUSTER_NODES")
    redis_max_connections: int = Field(default=50, alias="REDIS_MAX_CONNECTIONS")
    redis_socket_timeout: int = Field(default=5, alias="REDIS_SOCKET_TIMEOUT")
    redis_socket_connect_timeout: int = Field(default=5, alias="REDIS_SOCKET_CONNECT_TIMEOUT")
    
    # JWT Configuration
    jwt_secret_key: str = Field(default="change-me-in-production", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, alias="JWT_EXPIRATION_HOURS")
    
    # Session Configuration
    session_timeout_minutes: int = Field(default=30, alias="SESSION_TIMEOUT_MINUTES")
    session_cleanup_interval_minutes: int = Field(default=5, alias="SESSION_CLEANUP_INTERVAL_MINUTES")
    
    # Security
    password_min_length: int = Field(default=8, alias="PASSWORD_MIN_LENGTH")
    max_login_attempts: int = Field(default=3, alias="MAX_LOGIN_ATTEMPTS")
    account_lock_duration_minutes: int = Field(default=15, alias="ACCOUNT_LOCK_DURATION_MINUTES")
    
    # Celery Configuration
    celery_broker_url: str = Field(default="redis://localhost:6379/1", alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/2", alias="CELERY_RESULT_BACKEND")
    
    # InfluxDB Configuration
    influxdb_url: str = Field(default="http://localhost:8086", alias="INFLUXDB_URL")
    influxdb_token: Optional[str] = Field(default=None, alias="INFLUXDB_TOKEN")
    influxdb_org: str = Field(default="trading-platform", alias="INFLUXDB_ORG")
    influxdb_bucket: str = Field(default="market-data", alias="INFLUXDB_BUCKET")
    
    # Google Cloud Configuration
    gcp_project_id: Optional[str] = Field(default=None, alias="GCP_PROJECT_ID")
    gcp_secret_manager_enabled: bool = Field(default=False, alias="GCP_SECRET_MANAGER_ENABLED")
    
    # Service Ports
    api_gateway_port: int = Field(default=8000, alias="API_GATEWAY_PORT")
    websocket_service_port: int = Field(default=8001, alias="WEBSOCKET_SERVICE_PORT")
    market_data_engine_port: int = Field(default=8002, alias="MARKET_DATA_ENGINE_PORT")
    order_processor_port: int = Field(default=8003, alias="ORDER_PROCESSOR_PORT")
    analytics_service_port: int = Field(default=8004, alias="ANALYTICS_SERVICE_PORT")
    
    @property
    def database_url(self) -> str:
        """Construct database URL."""
        if self.use_pgbouncer and self.pgbouncer_host:
            host = self.pgbouncer_host
            port = self.pgbouncer_port
        else:
            host = self.db_host
            port = self.db_port
        
        return f"postgresql://{self.db_user}:{self.db_password}@{host}:{port}/{self.db_name}"
    
    @property
    def redis_url(self) -> str:
        """Construct Redis URL."""
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
