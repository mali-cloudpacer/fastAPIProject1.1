from fastapi import FastAPI, Depends, Request, HTTPException
from sqlalchemy.orm import relationship, sessionmaker, Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from models import DatabaseInfo, DatabaseInfoResponse
from DB_schema import postgreSQL_schema_info, execute_query
from typing import List
from database import get_db, tabel_migrations
from sqlalchemy.future import select
import pandas as pd

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



@app.get("/runquery/{query}")
async def run_query(query: str):
    results, error_msg = execute_query(query=query, dbname='ibmhr',
    user='postgres',
    password='nopassword',
    host='localhost',
    port=5432)

    return {"results":{"query_results": results, "query":query}, "Error_Msg": error_msg}



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
