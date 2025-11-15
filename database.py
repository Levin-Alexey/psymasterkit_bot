from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from models import Base
import os
from loguru import logger
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable is not set. Please set it to your PostgreSQL connection string.")
    raise ValueError("DATABASE_URL environment variable is required")

# Create the async SQLAlchemy engine
engine = create_async_engine(DATABASE_URL, echo=False)

# Create a configured "AsyncSession" class
AsyncSessionLocal = async_sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)


async def init_db():
    """Initializes the database by creating all tables defined in Base."""
    logger.info(f"Initializing database at {DATABASE_URL}")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully or already exist.")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")


async def get_db():
    """Dependency to get an async database session."""
    async with AsyncSessionLocal() as session:
        yield session
