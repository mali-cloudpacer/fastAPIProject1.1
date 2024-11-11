from langchain_openai import ChatOpenAI
import os, chromadb
from sentence_transformers import SentenceTransformer
from DB_schema import postgreSQL_schema_info
from langchain import PromptTemplate, LLMChain
from langchain_huggingface import HuggingFaceEndpoint
from dotenv import load_dotenv

# os.environ["LANGCHAIN_TRACING_V2"] = "true"
# os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"
# os.environ["LANGCHAIN_API_KEY"] = "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"
# os.environ["LANGCHAIN_PROJECT"] = "pr-prickly-granddaughter-44"
# os.environ["OPENAI_API_KEY"] = "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"





# llm = ChatOpenAI()
# llm.invoke("Hello, world!")

def create_vector_DB():
    model, collection = None, None
    try:
        os.environ["HUGGINGFACEHUB_API_TOKEN"] = "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"

        load_dotenv('.env.local')

        storage_path = os.getenv('VECTOR_STORAGE_PATH')
        if not storage_path:
            raise ValueError('VECTOR_STORAGE_PATH environment variable is not set')

        client = chromadb.PersistentClient(path=storage_path)

        collection = client.get_or_create_collection("db_embendings")


        model = SentenceTransformer('all-MiniLM-L6-v2')
        schema_info, all_tables_names, error_msg = postgreSQL_schema_info()
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
                    metadatas=[{"table_index": idx, "source": "postgreSQl_DB"}]
                )

        else:
            print(error_msg)

    except Exception as e:
        print(e)
    finally:
        return model, collection


def query_vector_DB(query_text, model, collection):
    result = None
    try:
        query_embedding = model.encode(query_text)

        # Retrieve similar documents
        results = collection.query(query_embeddings=[query_embedding], n_results=5)

        for result in results['documents']:
            print(result)
    except Exception as e:
        print(e)
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
        template = f"""
            You are given a question and table information. Generate only the SQL query if it can be constructed based on the table information provided. If the table is not relevant to the question or if no query can be constructed, respond with "None" only. 

            Question: {question}

            Context (Table Information):
            {context}

            Query:
            """

        # Define input variables for RAG model to retrieve relevant context and generate answer
        prompt = PromptTemplate(template=template, input_variables=["question", "context"])
        print(prompt)
        llm_chain = LLMChain(llm=llm, prompt=prompt)
        response = llm_chain.invoke({
            "question": question,
            "context": context
        })
        print(response.get('text', "NO key"))
    except Exception as e:
        print(e)
    finally:
        return response
