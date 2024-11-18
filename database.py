from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from models import Base
from logging.config import fileConfig
from alembic import context
from typing import AsyncGenerator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session

config = {
    'dbname': 'nl2sql',
    'user': 'postgres',
    'password': 'nopassword',
    'host': 'localhost',
    'port': '5432',
}
# Configure the async PostgreSQL database URL
DATABASE_URL = f"postgresql+asyncpg://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['dbname']}"

DATABASE_URL_SYNC = f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['dbname']}"

# Set up database engine and session
engine = create_async_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)

# Set up database engine and session for sync operations
engine_sync = create_engine(DATABASE_URL_SYNC, echo=True)
SessionLocalSync = sessionmaker(autocommit=False, autoflush=False, bind=engine_sync)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def tabel_creation():
    async with engine.begin() as conn:
        print("Table creation started")
        await conn.run_sync(Base.metadata.create_all)



def get_db_sync():
    db = SessionLocalSync()
    try:
        return db
    finally:
        db.close()

def table_creation_sync():
    with engine_sync.connect() as conn:
        print("Table creation started")
        Base.metadata.create_all(conn)