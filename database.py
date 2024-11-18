from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from models import Base
from logging.config import fileConfig
from alembic import context
from typing import AsyncGenerator


config = {
    'dbname': 'nl2sql',
    'user': 'postgres',
    'password': 'nopassword',
    'host': 'localhost',
    'port': '5432',
}
# Configure the async PostgreSQL database URL
DATABASE_URL = f"postgresql+asyncpg://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['dbname']}"

# Set up database engine and session
engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def tabel_creation():
    async with engine.begin() as conn:
        print("Table creation started")
        await conn.run_sync(Base.metadata.create_all)