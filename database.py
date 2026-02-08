"""
Database Manager for AI Grocery Agent - Production Version

Handles:
- PostgreSQL connection pool setup
- Schema creation
- Session management
- Health checks

**PRODUCTION:** No mock data seeding. Database must be populated via API.
"""

import logging
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages PostgreSQL connection and schema initialization"""
    
    def __init__(self, db_url: str, echo: bool = False):
        """
        Initialize database manager.
        
        Args:
            db_url: PostgreSQL connection string (e.g., postgresql://user:pass@localhost/grocery)
            echo: Enable SQL logging if True
        """
        self.db_url = db_url
        
        # Create engine with connection pooling
        self.engine = create_engine(
            db_url,
            poolclass=QueuePool,
            pool_size=10,
            max_overflow=20,
            pool_pre_ping=True,  # Verify connections are alive
            echo=echo
        )
        
        # Create session factory
        self.SessionLocal = sessionmaker(
            bind=self.engine,
            expire_on_commit=False
        )
        
        logger.info(f"DatabaseManager initialized with {db_url}")
    
    def init_db(self) -> None:
        """
        Create schema and all tables.

        **PRODUCTION:** Only creates schema. Does NOT seed data.
        Database must be populated via SERPAPI fetches.
        """
        try:
            from models import Base

            # Create all tables
            Base.metadata.create_all(self.engine)
            logger.info("✓ Database schema initialized successfully")

            # Verify tables exist
            inspector = inspect(self.engine)
            tables = inspector.get_table_names(schema='grocery')
            logger.info(f"✓ Created tables: {tables}")

        except Exception as e:
            logger.error(f"✗ Failed to initialize database: {e}")
            raise

    def get_session(self) -> Session:
        """
        Get a new database session.
        
        Returns:
            SQLAlchemy Session object
        """
        return self.SessionLocal()
    
    @contextmanager
    def session_scope(self):
        """
        Provide a transactional scope around a series of operations.
        
        Usage:
            with db_manager.session_scope() as session:
                # Use session
                pass
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()
    
    def health_check(self) -> bool:
        """
        Check if database is accessible.
        
        Returns:
            True if connected and responsive
        """
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("✓ Database health check passed")
            return True
        except Exception as e:
            logger.error(f"✗ Database health check failed: {e}")
            return False
    
    def close(self) -> None:
        """Close all connections in the pool"""
        try:
            self.engine.dispose()
            logger.info("✓ Database connection pool closed")
        except Exception as e:
            logger.error(f"Error closing database: {e}")


# Convenience function for global access
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """
    Get global database manager instance.
    Initialize if not already created.
    """
    global _db_manager
    
    if _db_manager is None:
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        db_url = os.getenv(
            "DATABASE_URL",
            "postgresql://peilin:peilin_passwd@localhost:5432/peilin_database"
        )
        _db_manager = DatabaseManager(db_url)
    
    return _db_manager


if __name__ == "__main__":
    # Test database connection and initialization
    import os
    from dotenv import load_dotenv

    load_dotenv()
    db_url = os.getenv("DATABASE_URL")

    if db_url:
        print(f"Initializing database: {db_url}")
        db = DatabaseManager(db_url, echo=False)

        # Check connection
        if db.health_check():
            print("✓ Connected to database")
        else:
            print("✗ Failed to connect to database")
            exit(1)

        # Initialize schema (run once)
        # db.init_db()

        print("\nNote: Database will be populated via SERPAPI when fetching prices")

        db.close()
    else:
        print("✗ DATABASE_URL not set in environment")
        exit(1)
