
import os
import weaviate
from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

def create_weaviate_client():
    """
    Weaviate client initialization module.

    This module is responsible for:
        - Loading environment variables from the .env file.
        - Retrieving OpenAI and Weaviate connection settings.
        - Providing a function to create a Weaviate client connected to a local instance.

    Environment variables:
        - OPENAI_API_KEY: API key for OpenAI (used in the Weaviate headers).
        - WEAVIATE_HOST (default: "127.0.0.1"): Host address of the Weaviate instance.
        - WEAVIATE_HOST_PORT (default: 11000): REST API port of the Weaviate instance.
        - WEAVIATE_GRPC_PORT (default: 50051): gRPC port of the Weaviate instance.

    Usage example:
        from weaviate_client import create_weaviate_client

        client = create_weaviate_client()
        print(client.is_ready())  # Check if Weaviate is up and running
    """
    
    host = os.getenv("WEAVIATE_HOST", "127.0.0.1")
    port = int(os.getenv("WEAVIATE_HOST_PORT", 11000))
    grpc_port = int(os.getenv("WEAVIATE_GRPC_PORT", 50051))
    
    return weaviate.connect_to_local(
        host=host,
        port=port,
        grpc_port=grpc_port,
        headers={"X-OpenAI-Api-Key": OPENAI_API_KEY}
    )