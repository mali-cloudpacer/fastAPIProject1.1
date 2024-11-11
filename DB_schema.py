import psycopg2
from collections import defaultdict
from psycopg2 import sql, OperationalError, ProgrammingError, InterfaceError
import time

from sqlalchemy.dialects.oracle.dictionary import all_tables


def postgreSQL_schema_info(**db_config ):
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


        for table, columns in tables.items():
            all_table_names.append(table)
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



def execute_query(** db_config):
    """
        Execute a PostgreSQL query with exception handling.

        :param connection_params: Dictionary containing connection parameters.
        :param query: The SQL query to be executed.
    """
    required_params = {'dbname', 'user', 'password', 'host', 'port'}
    missing_params = required_params - db_config.keys()

    if missing_params:
        return f"Missing parameters: {', '.join(missing_params)}"
    results = None
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
            results = cursor.fetchall()  # Fetch the results
            conn.commit()
            print("Query executed successfully.")

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
        return results, error_msg






