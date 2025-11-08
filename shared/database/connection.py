"""
Database connection management with connection pooling.
Supports PgBouncer integration for production deployments.
"""
import logging
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine, event, pool
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool

from shared.config import get_settings

logger = logging.getLogger(__name__)

# Base class for all models
Base = declarative_base()


class DatabaseManager:
    """Manages database connections with connection pooling."""
    
    def __init__(self):
        self.settings = get_settings()
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None
    
    def initialize(self) -> None:
        """Initialize database engine and session factory."""
        if self._engine is not None:
            logger.warning("Database already initialized")
            return
        
        # Create engine with connection pooling
        self._engine = create_engine(
            self.settings.database_url,
            poolclass=QueuePool,
            pool_size=self.settings.db_pool_size,
            max_overflow=self.settings.db_max_overflow,
            pool_timeout=self.settings.db_pool_timeout,
            pool_recycle=self.settings.db_pool_recycle,
            pool_pre_ping=True,  # Verify connections before using
            echo=self.settings.debug,
        )
        
        # Configure connection pool events
        self._setup_pool_events()
        
        # Create session factory
        self._session_factory = sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False
        )
        
        logger.info(
            f"Database initialized: {self.settings.db_host}:{self.settings.db_port}/{self.settings.db_name}"
        )
        
        if self.settings.use_pgbouncer:
            logger.info(f"Using PgBouncer: {self.settings.pgbouncer_host}:{self.settings.pgbouncer_port}")
    
    def _setup_pool_events(self) -> None:
        """Set up connection pool event listeners."""
        
        @event.listens_for(self._engine, "connect")
        def receive_connect(dbapi_conn, connection_record):
            """Handle new connection creation."""
            logger.debug("New database connection established")
        
        @event.listens_for(self._engine, "checkout")
        def receive_checkout(dbapi_conn, connection_record, connection_proxy):
            """Handle connection checkout from pool."""
            logger.debug("Connection checked out from pool")
        
        @event.listens_for(self._engine, "checkin")
        def receive_checkin(dbapi_conn, connection_record):
            """Handle connection return to pool."""
            logger.debug("Connection returned to pool")
    
    @property
    def engine(self) -> Engine:
        """Get database engine."""
        if self._engine is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._engine
    
    @property
    def session_factory(self) -> sessionmaker:
        """Get session factory."""
        if self._session_factory is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._session_factory
    
    def create_session(self) -> Session:
        """Create a new database session."""
        return self.session_factory()
    
    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        Provide a transactional scope for database operations.
        
        Usage:
            with db_manager.session_scope() as session:
                session.query(User).all()
        """
        session = self.create_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def dispose(self) -> None:
        """Dispose of the database engine and close all connections."""
        if self._engine:
            self._engine.dispose()
            logger.info("Database connections disposed")
            self._engine = None
            self._session_factory = None
    
    def get_pool_status(self) -> dict:
        """Get current connection pool status."""
        if self._engine is None:
            return {"status": "not_initialized"}
        
        pool = self._engine.pool
        return {
            "size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "overflow": pool.overflow(),
            "total": pool.size() + pool.overflow()
        }


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def init_database() -> DatabaseManager:
    """Initialize the global database manager."""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
        _db_manager.initialize()
    return _db_manager


def get_db_manager() -> DatabaseManager:
    """Get the global database manager instance."""
    if _db_manager is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _db_manager


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Get a database session with automatic cleanup.
    
    Usage:
        with get_db_session() as session:
            users = session.query(User).all()
    """
    db_manager = get_db_manager()
    with db_manager.session_scope() as session:
        yield session
