from fastapi import FastAPI, Depends, Request, HTTPException
from sqlalchemy.orm import relationship, sessionmaker, Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from models import DatabaseInfo, DatabaseInfoResponse, DatabaseCredsCreate, DatabaseCreds, DatabaseCredsUpdate, QueryRequest
from DB_schema import postgreSQL_schema_info, execute_query
from typing import List
from database import get_db, tabel_migrations
from sqlalchemy.future import select
import pandas as pd
from dataclasses import asdict
import json
import psycopg2

app = FastAPI()


# Database Configuration
employee_config = {
    'dbname': 'ibmhr',
    'user': 'postgres',
    'password': 'nopassword',
    'host': 'localhost',
    'port': '5432',
}





@app.on_event("startup")
async def startup():
    print("SERVER is booting up")
    # Create the database tables
    await tabel_migrations()
    print("SERVER is started")


@app.get("/schema_info/")
def get_db_schema(db: Session = Depends(get_db)):
    Schema_info, all_table_names ,error_msg = postgreSQL_schema_info(dbname='ibmhr',
    user='postgres',
    password='nopassword',
    host='localhost',
    port=5432)

    return {"results":{ "schema_info": Schema_info,"all_table_names": all_table_names} ,"Error_Msg":error_msg}
@app.post("/get-query")
async def get_query(request: Request):
    pass
    # Get query parameters from the body (request query)




@app.post("/runquery/")
async def run_query(request: QueryRequest,  db: AsyncSession = Depends(get_db)):
    # Validate query to ensure it's a SELECT statement only
    query = request.query.strip()
    if not query.lower().startswith("select"):
        raise HTTPException(status_code=400, detail="Only SELECT queries are allowed.")

    result = await db.execute(select(DatabaseCreds).filter(DatabaseCreds.id == request.DatabaseCreds_id))
    db_creds = result.scalars().first()
    if db_creds is None:
        raise HTTPException(status_code=404, detail="DatabaseCreds not found")


    db_creds_data = {key: getattr(db_creds, key) for key in vars(db_creds) if not key.startswith('_')}
    db_creds_data = db_creds_data['connection_creds']
    db_creds_data['query'] = query

    results, error_msg = execute_query(**db_creds_data)

    return {"results": {"query_results": results, "query": query}, "Error_Msg": error_msg}


@app.get("/")
async def root():
    return {"message": "Hello World"}


@app.get("/hello/{name}")
async def say_hello(name: str):
    return {"message": f"Hello {name}"}



@app.get("/database_forms/", response_model=List[DatabaseInfoResponse])
async def get_all_database_info(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DatabaseInfo))
    database_info = result.scalars().all()
    if not database_info:
        raise HTTPException(status_code=404, detail="No database info found.")
    return database_info


# Function to validate the connection with the provided credentials
def validate_connection(db_type: str, connection_creds: dict):
    try:
        if db_type == "PostgreSQL":
            # Check PostgreSQL connection as an example
            conn = psycopg2.connect(
                dbname=connection_creds["dbname"],
                user=connection_creds["user"],
                password=connection_creds["password"],
                host=connection_creds["host"],
                port=connection_creds["port"]
            )
            conn.close()
            return True
        else:
            raise HTTPException(status_code=400, detail="Unsupported database type.")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Connection failed: {e}")

async def valid_db_creds(db_creds: DatabaseCredsCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DatabaseInfo).filter(DatabaseInfo.id == db_creds.database_info_id))
    db_info = result.scalars().first()
    if db_info is None:
        raise HTTPException(status_code=404, detail="DatabaseInfo not found")

    # Validate the structure of connection_creds
    try:
        json.loads(json.dumps(db_creds.connection_creds))
        valid_creds = db_info.connection_structure.keys() == db_creds.connection_creds.keys()
        valid_type = db_info.db_type == db_creds.db_type
        if not valid_creds or not valid_type:
            raise HTTPException(status_code=400, detail=f"Invalid Credentials JSON structure/ DB type")

        return validate_connection(db_creds.db_type, db_creds.connection_creds)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON structure: {e}")





# Create DatabaseCreds
@app.post("/database_creds/", response_model=DatabaseCredsCreate)
async def create_database_creds(db_creds: DatabaseCredsCreate, db: AsyncSession = Depends(get_db)):
    # Check if DatabaseInfo exists
    valid = await valid_db_creds(db_creds, db)

    if valid:
        db_creds_db = DatabaseCreds(
            database_info_id=db_creds.database_info_id,
            db_type=db_creds.db_type,
            connection_creds=db_creds.connection_creds
        )
        async with db as session:
            session.add(db_creds_db)
            await session.commit()
            await session.refresh(db_creds_db)

        return db_creds_db
    else:
        return {'Error': 'Database is not valid'}

@app.get("/database_creds/", response_model=List[DatabaseCredsUpdate])
async def get_all_database_creds(db: AsyncSession = Depends(get_db)):
    # Query to select all records from DatabaseCreds
    result = await db.execute(select(DatabaseCreds))
    db_creds_list = result.scalars().all()

    # Check if there are any records, if not return an empty list
    if not db_creds_list:
        return []

    return db_creds_list

@app.put("/database_creds/", response_model=DatabaseCredsUpdate)
async def update_database_creds( db_creds: DatabaseCredsUpdate, db: AsyncSession = Depends(get_db)):
    # Fetch the existing database credential entry
    result = await db.execute(select(DatabaseCreds).filter(DatabaseCreds.id == db_creds.id))
    existing_creds = result.scalars().first()

    # Check if the record exists
    if existing_creds is None:
        raise HTTPException(status_code=404, detail="Database credentials not found")

    db_creds_data = db_creds.dict()
    db_creds_data.pop("id")

    # Create a DatabaseCredsCreate instance from the updated data without the 'id' field
    db_creds = DatabaseCredsCreate(**db_creds_data)
    valid = await valid_db_creds(db_creds, db)

    if valid:
        existing_creds.database_info_id = db_creds.database_info_id
        existing_creds.db_type = db_creds.db_type
        existing_creds.connection_creds = db_creds.connection_creds

        # Commit the changes to the database
        async with db as session:
            session.add(existing_creds)
            await session.commit()
            await session.refresh(existing_creds)

        return existing_creds
    else:
        return {'Error': 'Database creds is not valid'}


@app.delete("/database_creds/{creds_id}")
async def delete_database_creds(creds_id: int, db: AsyncSession = Depends(get_db)):
    # Fetch the existing database credential entry
    result = await db.execute(select(DatabaseCreds).filter(DatabaseCreds.id == creds_id))
    existing_creds = result.scalars().first()

    # Check if the record exists
    if existing_creds is None:
        raise HTTPException(status_code=404, detail="Database credentials not found")

    # Delete the database credential entry
    await db.delete(existing_creds)
    await db.commit()

    return {"message": "Database credentials deleted successfully"}