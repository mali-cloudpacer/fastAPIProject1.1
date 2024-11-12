from sqlalchemy import Column, Integer, String, JSON, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from pydantic import BaseModel

class DatabaseInfoResponse(BaseModel):
    id: int
    db_type: str
    connection_structure: dict

    class Config:
        orm_mode = True

class DatabaseInfo(Base):
    __tablename__ = "database_info"

    id = Column(Integer, primary_key=True, index=True)
    db_type = Column(String, nullable=False)
    connection_structure = Column(JSON, nullable=False)

    # Establish a one-to-many relationship with DatabaseCreds
    creds = relationship("DatabaseCreds", back_populates="database_info")

class DatabaseCredsCreate(BaseModel):
    database_info_id: int
    db_type: str
    connection_creds: dict

class DatabaseCredsUpdate(BaseModel):
    id: int
    database_info_id: int
    db_type: str
    connection_creds: dict

class DatabaseCreds(Base):
    __tablename__ = "database_creds"

    id = Column(Integer, primary_key=True, index=True)
    database_info_id = Column(Integer, ForeignKey("database_info.id"), nullable=False)  # Foreign key column
    db_type = Column(String, nullable=False)
    connection_creds = Column(JSON, nullable=False)

    # Set up relationship back to DatabaseInfo
    database_info = relationship("DatabaseInfo", back_populates="creds")
