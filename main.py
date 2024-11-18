from fastapi import FastAPI, Depends, Request, HTTPException
import subprocess, asyncio, asyncpg
from sqlalchemy.orm import relationship, sessionmaker, Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from starlette.responses import Response
from stem.interpreter.help import response
from fastapi.responses import JSONResponse

from models import (DatabaseInfo, DatabaseInfoResponse, DatabaseCredsCreate,
                    DatabaseCreds, DatabaseCredsUpdate, QueryRequest, DB_type, ConnectionStructureRequest)
from DB_schema import postgreSQL_schema_info, postgresql_execute_query
from typing import List
from database import get_db, tabel_creation
from sqlalchemy.future import select
import pandas as pd
from dataclasses import asdict
import json
import psycopg2
from vector_DB import sync_schema_create_vector_DB
from DB_schema import check_schema_changes, get_current_schema_hash_postgresql

app = FastAPI()


# Database Configuration
employee_config = {
    'dbname': 'ibmhr',
    'user': 'postgres',
    'password': 'nopassword',
    'host': 'localhost',
    'port': '5432',
}


def make_migration():
    """Generates a new migration file if model changes are detected."""
    try:
        result = subprocess.run(
            ["alembic", "revision", "--autogenerate", "-m", "auto migration"],
            capture_output=True,
            text=True,
            check=False
        )
        output = result.stdout + result.stderr
        print("auto Migration output: ",output)
        if "No changes in schema detected".lower() in str(output):
            print("No schema changes detected. Skipping migration file creation.")
            return False
        elif result.returncode == 0:
            print("Migration file created successfully.")
            return True
        else:
            print("Error generating migration:", output)
            return False
    except subprocess.CalledProcessError as e:
        print("Error generating migration:", e)
        return False

def migrate_migration():
    """Applies all pending migrations if there are any."""
    try:
        subprocess.run(
            ["alembic", "upgrade", "head"],
            check=True
        )
        print("Migrations applied successfully.")
    except subprocess.CalledProcessError as e:
        print("Error applying migrations:", e)

@app.on_event("startup")
async def startup():
    print("SERVER is booting up")

    # Step 1: Create the database tables
    await tabel_creation()

    # if make_migration():
    #     migrate_migration()

    print("SERVER is started")


@app.get("/schema_info/")
def get_db_schema(db: Session = Depends(get_db)):
    # Schema_info, all_table_names ,error_msg = postgreSQL_schema_info(dbname='ibmhr',
    # user='postgres',
    # password='nopassword',
    # host='localhost',
    # port=5432)
    pass


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

    if db_creds.db_type == DB_type.PostgreSQL.value:
        results, error_msg = postgresql_execute_query(**db_creds_data)
    else:
        results, error_msg = [], "query execution in not available for db: "+db_creds.db_type

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
def validate_connection(db_type: str, connection_creds: dict) -> tuple[bool, str]:
    try:
        if db_type == DB_type.PostgreSQL.value:
            # Check PostgreSQL connection as an example
            conn = psycopg2.connect(
                dbname=connection_creds["dbname"],
                user=connection_creds["user"],
                password=connection_creds["password"],
                host=connection_creds["host"],
                port=connection_creds["port"]
            )
            conn.close()
            return True,""
        else:
            return False, "Unsupported database type."
    except Exception as e:
        return False, f"Connection failed: {e}"

async def valid_db_creds(db_creds: DatabaseCredsCreate, db: AsyncSession ) -> tuple[bool,str]:
    result = await db.execute(select(DatabaseInfo).filter(DatabaseInfo.id == db_creds.database_info_id))
    db_info = result.scalars().first()
    if db_info is None:
        return False, "DatabaseInfo not found"

    # Validate the structure of connection_creds
    try:
        json.loads(json.dumps(db_creds.connection_creds))
        valid_creds = db_info.connection_structure.keys() == db_creds.connection_creds.keys()
        valid_type = db_info.db_type == db_creds.db_type
        if not valid_creds or not valid_type:
            raise HTTPException(status_code=400, detail=f"Invalid Credentials JSON structure/ DB type")

        valid, msg = validate_connection(db_creds.db_type, db_creds.connection_creds)

        return valid, msg
    except ValueError as e:
        return False, f"Invalid JSON structure: {e}"





# Create DatabaseCreds
@app.post("/database_creds/")
async def create_database_creds(db_creds: DatabaseCredsCreate, db: AsyncSession = Depends(get_db)):
    # Check if DatabaseInfo exists
    valid, msg = await valid_db_creds(db_creds, db)

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

        sync_schema_create_vector_DB(db_creds_db.id)

        return JSONResponse(status_code=200, content={'Result': 'Database added successfully', 'Error': ''})
    else:
        return JSONResponse(status_code=400, content={"Results": "Connection failed", "Error": msg})






@app.post("/test-db-connection")
async def test_db_connection(request: ConnectionStructureRequest, db_session: AsyncSession = Depends(get_db)):
    # Retrieve the DatabaseInfo record using the provided db_id
    result = await db_session.execute(
        select(DatabaseInfo).filter(DatabaseInfo.id == request.db_info_id)
    )
    db_info = result.scalar_one_or_none()
    if not db_info:
        return JSONResponse(status_code=404, content={"Results": "Connection failed", "Error": "DatabaseInfo not found"})

    # Verify the connection structure has the required keys and make a connection
    valid, msg = validate_connection(db_type= db_info.db_type,connection_creds=request.connection_creds)

    if valid:
        return JSONResponse(status_code=200, content={"Results":"connection successful", "Error":""})
    else:
        return JSONResponse(status_code=400, content={"Results": "Connection failed", "Error": msg})


@app.get("/change-db-schema/{db_creds_id}")
async def change_db_schema(db_creds_id:int , db_session: AsyncSession = Depends(get_db)):
    # Retrieve the DatabaseInfo record using the provided db_id
    result = await db_session.execute(
        select(DatabaseCreds).filter(DatabaseCreds.id == db_creds_id)
    )
    db_creds = result.scalar_one_or_none()
    if not db_creds:
        return JSONResponse(status_code=404,
                            content={"Results": "Connection failed", "Error": "Databasecreds not found"})

    if db_creds.db_type == DB_type.PostgreSQL.value:
        new_hash_schema = get_current_schema_hash_postgresql(**db_creds.connection_creds)
    else:
        return JSONResponse(status_code=400, content={"Results": "", "Error": db_creds.db_type+" has not hashing function / under development"})

    change_detect, changes = check_schema_changes(old_hashes=db_creds.table_hashes,new_hashes=new_hash_schema)

    if change_detect:
        return JSONResponse(status_code=200, content={"Results":changes, "Error":""})
    else:
        return JSONResponse(status_code=400, content={"Results": "no changes detected", "Error": ""})



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
    valid, msg = await valid_db_creds(db_creds, db)

    if valid:
        existing_creds.database_info_id = db_creds.database_info_id
        existing_creds.db_type = db_creds.db_type
        existing_creds.connection_creds = db_creds.connection_creds

        # Commit the changes to the database
        async with db as session:
            session.add(existing_creds)
            await session.commit()
            await session.refresh(existing_creds)

        return JSONResponse(status_code=200, content={"Results":existing_creds,"Error": ""})
    else:
        return JSONResponse(status_code=400, content={"Results":"","Error": msg})


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