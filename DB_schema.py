import psycopg2
from collections import defaultdict
from psycopg2 import sql, OperationalError, ProgrammingError, InterfaceError
import time, json
import hashlib
from models import DatabaseCreds
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db
from fastapi import Depends
from sqlalchemy.dialects.oracle.dictionary import all_tables


async def postgreSQL_schema_info(db_cred_obj: DatabaseCreds, db: AsyncSession = Depends(get_db)) -> tuple[list, str, str]:
        db_config = db_cred_obj.connection_creds
        required_params = {'dbname', 'user', 'password', 'host', 'port'}
        missing_params = required_params - db_config.keys()

        if missing_params:
            return [],"", f"Missing parameters: {', '.join(missing_params)}"

        Db_info = []
        all_table_names = []
        table_info = ""
        error_msg = ""
        try:
            connection = psycopg2.connect(**db_config)
            cursor = connection.cursor()

            # Query to get table schema details
            query = """
            SELECT
                table_name,
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM
                information_schema.columns
            WHERE
                table_schema = 'public'
            ORDER BY
                table_name, ordinal_position;
            """
            cursor.execute(query)

            # Fetch all results
            schema_info = cursor.fetchall()
            tables = defaultdict(list)
            for row in schema_info:
                tables[row[0]].append({
                    'Column': row[1],
                    'Type': row[2],
                    'Nullable': row[3],
                    'Default': row[4]
                })

            table_hashes = {}

            for table, columns in tables.items():
                all_table_names.append(table)
                # Sort columns by name for consistency in hashing
                columns = sorted(columns, key=lambda col: col['Column'])

                # Create a unique string based on table structure
                table_schema_string = json.dumps(columns, sort_keys=True)

                # Generate a hash for this table's schema
                table_hash = hashlib.sha256(table_schema_string.encode()).hexdigest()

                table_hashes[table] = table_hash
                table_info += f"\nTable: {table}\n"
                table_info += "  Column".ljust(25) + "Type".ljust(20) + "Nullable".ljust(10) + "Default\n"
                table_info +=  "-" * 65
                table_info += "\n"
                for column in columns:

                        table_info += f"  {column['Column'].ljust(25)}"
                        table_info +=  f"{column['Type'].ljust(20)}"
                        table_info +=  f"{column['Nullable'].ljust(10)}"
                        table_info +=  f"{str(column['Default'])}"
                table_info += "\n"
                Db_info.append(table_info)

            db_cred_obj.table_hashes = table_hashes
            try:
                if db.is_active:  # Check if the session is active
                    async with db.begin():  # Begin a new transaction
                        db.add(db_cred_obj)
                        await db.commit()
                        await db.refresh(db_cred_obj)
                else:
                    print("Session is not active. Starting a new transaction...")
                    async with AsyncSession() as new_db:  # Create a new session if the previous is closed
                        async with new_db.begin():
                            new_db.add(db_cred_obj)
                            await new_db.commit()
                            await new_db.refresh(db_cred_obj)
            except Exception as e:
                print(f"An error occurred: {e}")



        except psycopg2.Error as e:
            error_msg = "Error connecting to PostgreSQL database:" + str(e)
            print(error_msg)
        finally:
            try:
                if cursor:
                    cursor.close()
                if connection:
                    connection.close()
            except Exception as e:
                error_msg = "Error closing PostgreSQL connection:" + str(e)
                print(error_msg)

            return Db_info, str(all_table_names) ,error_msg



def postgresql_execute_query(** db_config):
    """
        Execute a PostgreSQL query with exception handling.

        :param connection_params: Dictionary containing connection parameters.
        :param query: The SQL query to be executed.
    """
    required_params = {'dbname', 'user', 'password', 'host', 'port'}
    missing_params = required_params - db_config.keys()

    if missing_params:
        return f"Missing parameters: {', '.join(missing_params)}"
    data_with_headers = None
    error_msg = ""
    try:
        # Establish a connection to the PostgreSQL database
        query = db_config.pop('query')
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()

        try:
            # Execute the query
            start_time = time.time()
            cursor.execute(query)
            column_headers = [desc[0] for desc in cursor.description]  # Get column headers
            results = cursor.fetchall()  # Fetch the results
            conn.commit()
            print("Query executed successfully.")

            # Combine headers with data
            data_with_headers = [dict(zip(column_headers, row)) for row in results]


        except ProgrammingError as e:
            error_msg =f"Syntax error in SQL query: {e}"
            print(error_msg)

        except OperationalError as e:
            if 'timeout' in str(e).lower():
                error_msg ="Query failed due to timeout."
            else:
                error_msg =f"Operational error: {e}"
            print(error_msg)
        finally:
            # Close the cursor and connection
            cursor.close()
            conn.close()
            print("Database connection closed.")

    except InterfaceError as e:
        error_msg =f"Database connection error: {e}"
        print(error_msg)

    except Exception as e:
        error_msg =f"An unexpected error occurred: {e}"
        print(error_msg)

    finally:
        return data_with_headers, error_msg


def get_current_schema_hash_postgresql(**db_config):
    connection = psycopg2.connect(**db_config)
    cursor = connection.cursor()

    query = """
    SELECT
        table_name,
        column_name,
        data_type,
        is_nullable,
        column_default
    FROM
        information_schema.columns
    WHERE
        table_schema = 'public'
    ORDER BY
        table_name, ordinal_position;
    """
    cursor.execute(query)

    # Fetch all results
    schema_info = cursor.fetchall()

    # Structure to store the schema details
    tables = defaultdict(list)
    for row in schema_info:
        tables[row[0]].append({
            'Column': row[1],
            'Type': row[2],
            'Nullable': row[3],
            'Default': row[4]
        })

    # Generate hash for each table schema
    table_hashes = {}
    for table, columns in tables.items():
        # Sort columns by name for consistency in hashing
        columns = sorted(columns, key=lambda col: col['Column'])

        # Create a unique string based on table structure
        table_schema_string = json.dumps(columns, sort_keys=True)

        # Generate a hash for this table's schema
        table_hash = hashlib.sha256(table_schema_string.encode()).hexdigest()

        table_hashes[table] = table_hash

    return table_hashes


def check_schema_changes(new_hashes, old_hashes) -> tuple[bool, dict]:
    changes = {
        'added_tables': [],
        'removed_tables': [],
        'modified_tables': []
    }

    # Check for added and removed tables
    new_tables = set(new_hashes.keys())
    old_tables = set(old_hashes.keys())

    changes['added_tables'] = list(new_tables - old_tables)
    changes['removed_tables'] = list(old_tables - new_tables)

    # Check for modified tables
    for table in new_tables & old_tables:
        if new_hashes[table] != old_hashes[table]:
            changes['modified_tables'].append(table)

    change_detect = any(changes[key] for key in changes)

    return change_detect, changes

