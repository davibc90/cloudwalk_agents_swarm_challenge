
from langchain_openai import OpenAIEmbeddings
from config.weaviate_client import create_weaviate_client
from langchain.tools.retriever import create_retriever_tool
from langchain_weaviate.vectorstores import WeaviateVectorStore
from dotenv import load_dotenv
import os

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBEDDINGS_MODEL = os.getenv("EMBEDDINGS_MODEL", "text-embedding-3-small")
INDEX_NAME = os.getenv("INDEX_NAME", "RAG")
RETRIEVER_SCORE_THRESHOLD = os.getenv("RETRIEVER_SCORE_THRESHOLD", 0.6)
RETRIEVER_K = os.getenv("RETRIEVER_K", 8)
RETRIEVER_ALPHA = os.getenv("RETRIEVER_ALPHA", 0.5)

def initialize_retriever_for_rag():

    # Defines the embeddings model
    embeddings = OpenAIEmbeddings(openai_api_key=OPENAI_API_KEY, model=EMBEDDINGS_MODEL)
    weaviate_client = create_weaviate_client()

    # Initializes the WeaviateVectorStore
    db = WeaviateVectorStore(
        embedding=embeddings,
        client=weaviate_client,
        index_name=INDEX_NAME,
        text_key="content",
        use_multi_tenancy=False
    )

    # Returns the configured retriever based on the interface with the vector store
    retriever = db.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={
            "score_threshold": float(RETRIEVER_SCORE_THRESHOLD),
            "k": int(RETRIEVER_K),
            "alpha": float(RETRIEVER_ALPHA),
        }
    )

    # Returns the configured retriever tool ready for use by the agent
    retriever_tool = create_retriever_tool(
        retriever, 
        name="retriever_tool",
        description="Use this tool to retrieve relevant documents from the knowledge base based on the user's query"
    )

    return retriever_tool


