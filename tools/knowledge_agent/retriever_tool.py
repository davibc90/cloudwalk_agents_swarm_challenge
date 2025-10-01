
from langchain_openai import OpenAIEmbeddings
from config.weaviate_client import create_weaviate_client
from langchain.tools.retriever import create_retriever_tool
from langchain_weaviate.vectorstores import WeaviateVectorStore
from config.env_config import env

# Environment variables
OPENAI_API_KEY = env.openai_api_key
EMBEDDINGS_MODEL = env.embeddings_model
INDEX_NAME = env.index_name
RETRIEVER_SCORE_THRESHOLD = env.retriever_score_threshold
RETRIEVER_K = env.retriever_k
RETRIEVER_ALPHA = env.retriever_alpha

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
        description="Use this tool to retrieve relevant documents from the knowledge base based on the user's input"
    )

    return retriever_tool


