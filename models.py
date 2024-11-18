from sqlalchemy import Column, Integer, String, JSON, ForeignKey, Sequence
from sqlalchemy.orm import relationship
from sqlalchemy.orm import declarative_base
from pydantic import BaseModel
from enum import Enum
from typing import Optional

Base = declarative_base()

class DB_type(Enum):
    PostgreSQL = "PostgreSQL"
    MySQL = "MySQL"

class DatabaseInfoResponse(BaseModel):
    id: int
    db_type: str
    connection_structure: dict
    logo_url: str

    class Config:
        orm_mode = True

# Define the model for the database connection structure request payload
class ConnectionStructureRequest(BaseModel):
    db_info_id: int
    connection_creds: dict

class DatabaseCredsCreate(BaseModel):
    database_info_id: int
    db_type: str
    connection_creds: dict
    test_connection: Optional[bool] = True

class DatabaseCredsUpdate(BaseModel):
    id: int
    database_info_id: int
    db_type: str
    connection_creds: dict
    test_connection: Optional[bool] = True

class QueryRequest(BaseModel):
    DatabaseCreds_id: int
    query: str



class DatabaseInfo(Base):
    __tablename__ = "database_info"

    id = Column(Integer, Sequence('database_info_id_seq', start=1, increment=1), primary_key=True, index=True)
    db_type = Column(String, nullable=False)
    connection_structure = Column(JSON, nullable=False)
    logo_url = Column(String, nullable=True)

    creds = relationship("DatabaseCreds", back_populates="database_info")


class DatabaseCreds(Base):
    __tablename__ = "database_creds"

    id = Column(Integer, Sequence('database_creds_id_seq', start=1, increment=1), primary_key=True, index=True)
    database_info_id = Column(Integer, ForeignKey("database_info.id"), nullable=False)
    db_type = Column(String, nullable=False)
    connection_creds = Column(JSON, nullable=False)
    table_hashes = Column(JSON, nullable=True)

    database_info = relationship("DatabaseInfo", back_populates="creds")
