from fastapi import FastAPI, Depends, Request
from sqlalchemy.orm import relationship, sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from models import Employee, JobInfo, Department, PerformanceInfo
from DB_schema import postgreSQL_schema_info, execute_query
import pandas as pd

app = FastAPI()
Base = declarative_base()


# Database Configuration
config = {
    'dbname': 'ibmhr',
    'user': 'postgres',
    'password': 'nopassword',
    'host': 'localhost',
    'port': '5432',
}

# Format the database URL for SQLAlchemy
DATABASE_URL = f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['dbname']}"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

# Dependency to get DB Session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.on_event("startup")
def server_startup():
    print("Server started")


# FastAPI endpoint to view employees
@app.get("/employees/")
def get_employees(skip: int = 0, limit: int = 1000, db: Session = Depends(get_db)):
    return db.query(Employee).offset(skip).limit(limit).all()

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
