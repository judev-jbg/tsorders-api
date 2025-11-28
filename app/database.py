"""
Database configuration and connection management
"""
from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
import os
from dotenv import load_dotenv
import logging
import urllib.parse

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Database configuration
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "toolstock_amz")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = urllib.parse.quote_plus(os.getenv("DB_PASSWORD"))
DB_CHARSET = os.getenv("DB_CHARSET", "utf8")

# Create database URL
DATABASE_URL = (
    f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    f"?charset={DB_CHARSET}"
)

# Create engine
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,   # Recycle connections after 1 hour
    echo=False,          # Set to True for SQL query logging
    poolclass=NullPool   # Disable pooling for better compatibility with stored procedures
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for ORM models
Base = declarative_base()


def get_db():
    """
    Database dependency for FastAPI routes.
    Creates a new database session for each request.

    Usage:
        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            # Use db here
            pass
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def test_connection():
    """
    Test database connection.
    Returns True if connection is successful, False otherwise.
    """
    try:
        with engine.connect() as connection:
            query = text("SELECT * FROM ordersdetail LIMIT 1")
            result = connection.execute(query)
            logger.info("✓ Database connection successful")
            return True
    except Exception as e:
        logger.error(f"✗ Database connection failed: {str(e)}")
        return False


# Event listener to handle multiple result sets from stored procedures
@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """
    Event listener to configure connection for stored procedures.
    This allows handling multiple result sets from MySQL stored procedures.
    """
    cursor = dbapi_conn.cursor()
    cursor.execute("SET SESSION sql_mode = 'TRADITIONAL'")
    cursor.close()
