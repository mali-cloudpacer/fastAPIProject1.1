from langchain_openai import ChatOpenAI
import os, chromadb
from sentence_transformers import SentenceTransformer
from DB_schema import postgreSQL_schema_info
from langchain import LLMChain
from langchain_core.prompts import PromptTemplate
from langchain_huggingface import HuggingFaceEndpoint
from dotenv import load_dotenv
from Decorators import run_in_background, run_in_background_async
from models import DatabaseCreds, DB_type
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_db, get_db_sync
from fastapi import Depends
from sqlalchemy.orm import Session



# os.environ["LANGCHAIN_TRACING_V2"] = "true"
# os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
# os.environ["LANGCHAIN_API_KEY"] = "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"
# os.environ["LANGCHAIN_PROJECT"] = "pr-prickly-granddaughter-44"
# os.environ["OPENAI_API_KEY"] = "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"





# llm = ChatOpenAI()
# llm.invoke("Hello, world!")
@run_in_background
def read_schema_create_update_vector_DB(db_cred_id: int):
    print("sync_schema_create_vector_DB function started")
    db: Session = get_db_sync()
    db_cred_obj = db.query(DatabaseCreds).filter(DatabaseCreds.id == db_cred_id).first()
    try:
        os.environ["HUGGINGFACEHUB_API_TOKEN"] = "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"

        load_dotenv('.env.local')

        storage_path = os.getenv('VECTOR_STORAGE_PATH')
        if not storage_path:
            raise ValueError('VECTOR_STORAGE_PATH environment variable is not set')

        client = chromadb.PersistentClient(path=storage_path)

        sql_db_config = db_cred_obj.connection_creds
        db_type = db_cred_obj.db_type


        collection_name = sql_db_config['dbname']+'_'+sql_db_config['host']+'_'+"db_embeddings"

        # Check if collection exists
        if collection_name in [c.name for c in client.list_collections()]:
            # If it exists, delete/truncate previous embeddings
            collection = client.get_collection(collection_name)
            client.delete_collection(collection_name)
            collection = client.create_collection(collection_name)
        else:
            # If not, create a new collection
            collection = client.create_collection(collection_name)

        model = SentenceTransformer('all-MiniLM-L6-v2')

        if db_type == DB_type.PostgreSQL.value:
            try:
                print("postgreSQL_schema_info calling")
                schema_info, all_tables_names, error_msg = postgreSQL_schema_info(db_cred_id)
                print("postgreSQL_schema_info ended")
            except Exception as e:
                schema_info, all_tables_names, error_msg = [],"",e
                print(e)
        else:
            return "DB type is not supported yet"
        embeddings = []
        chunks = []
        if schema_info:
            for table_info in schema_info:
                chunk = "Table Info:\n" + table_info + "\n\nAll tabel names: " + all_tables_names
                chunks.append(chunk)
                embeddings.append(model.encode(chunk))

            for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                # Use the index as a unique ID or create custom unique IDs
                unique_id = f"table_info_{idx}"

                collection.add(
                    ids=[unique_id],  # Assign a unique ID for each document
                    documents=[chunk],
                    embeddings=[embedding],
                    metadatas=[{"table_index": idx, "source": db_type}]
                )

        else:
            print(error_msg)

    except Exception as e:
        print(e)
    finally:
        print("read_schema_create_update_vector_DB function ended")

async def get_model_collection_vector_db(db_creds:DatabaseCreds):
    model, collection = None,None
    try:
        os.environ["HUGGINGFACEHUB_API_TOKEN"] = "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"

        load_dotenv('.env.local')

        storage_path = os.getenv('VECTOR_STORAGE_PATH')
        if not storage_path:
            raise ValueError('VECTOR_STORAGE_PATH environment variable is not set')

        client = chromadb.PersistentClient(path=storage_path)

        sql_db_config = db_creds.connection_creds
        db_type = db_creds.db_type


        collection_name = sql_db_config['dbname']+'_'+sql_db_config['host']+'_'+"db_embeddings"

        # Check if collection exists
        if collection_name in [c.name for c in client.list_collections()]:
            collection = client.get_collection(collection_name)
            model = SentenceTransformer('all-MiniLM-L6-v2')
        else:
            print("Collection not for the DB: DatabaseCreds_id "+str(db_creds.id))

    except Exception as e:
        print("Exception in get_model_collection_vector_db "+str(e))
    finally:
        return model, collection



def query_vector_DB(query_text, model, collection, num_results=3):
    result = None
    try:
        query_embedding = model.encode(query_text)

        # Retrieve similar documents
        results = collection.query(query_embeddings=[query_embedding], n_results=num_results)

        for result in results['documents']:
            print(result)
    except Exception as e:
        print("Exception in query_vector_DB functoin: "+str(e))
    finally:
        return result


def create_sql_query(query_text, table_info):
    response = None
    try:
        repo_id = "mistralai/Mistral-7B-Instruct-v0.2"
        # repo_id="mistralai/Mistral-7B-Instruct-v0.3"
        llm = HuggingFaceEndpoint(repo_id=repo_id, max_length=264, temperature=0.7,
                                  token="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")
        question = query_text
        context = str(table_info)
        # Define a template that can format retrieved context and structure an answer based on it
        template = """
            You are given a question and table information. Generate only the SQL query if it can be constructed based on the table information provided. If the table is not relevant to the question or if no query can be constructed, respond with "None" only. 

            Question: {question}

            Context (Table Information):
            {context}

            Query:
            """

        # Define input variables for RAG model to retrieve relevant context and generate answer
        prompt = PromptTemplate(template=template, input_variables=["question", "context"])
        print(prompt)
        llm_chain = LLMChain(llm=llm, prompt=prompt, name="create_sql_response_chain")
        response = llm_chain.invoke({
            "question": question,
            "context": context
        })
        response = response.get('text', "NO text response from LLM")
        print(response)
    except Exception as e:
        print("Exception in the create_sql_query: "+str(e))
    finally:
        print("create_sql_query ended")
        print("llm response: "+str(response))
        return response

def create_nl_response(query_text, query_results, sql_query):
    response = None
    try:
        repo_id = "mistralai/Mistral-7B-Instruct-v0.2"
        # repo_id="mistralai/Mistral-7B-Instruct-v0.3"
        llm = HuggingFaceEndpoint(repo_id=repo_id, max_length=512, temperature=0.7,
                                  token="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")

        question = query_text
        context = f"(sql_query: {sql_query}), (query_results: {query_results})"


        # Define a template that can format retrieved context and structure an answer based on it
        template = """
                    You are given a question, sql_query and query_results. Give me information in Natural Language based on the query_results table information. If the table is not relevant to the question , respond with "Question and Data are not Matching" only.

                    Question: {question}

                    Context:{context}


                    Answer:
                    """

        # Define input variables for RAG model to retrieve relevant context and generate answer
        prompt = PromptTemplate(template=template, input_variables=["question", "context"])
        print(prompt)
        llm_chain = LLMChain(llm=llm, prompt=prompt, name="create_nl_response_chain")
        response = llm_chain.invoke({
            "question": question,
            "context": context
        })
        response = response.get('text', "NO text response from LLM")
        print(response)
    except Exception as e:
        print("Exception in the create_nl_response: "+str(e))
    finally:
        print("create_nl_response ended")
        print("llm response: "+str(response))
        return response
