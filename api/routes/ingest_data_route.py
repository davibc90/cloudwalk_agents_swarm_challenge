from fastapi import HTTPException, APIRouter
from utils.logger_utils import setup_logger
from services.ingest_data import ingest_urls_to_weaviate
from api.schemas.ingest_data_schema import IngestRequest, IngestResponse, IngestResult
from config.env_config import env

logger = setup_logger(__name__)

INDEX_NAME = env.index_name
EMBEDDINGS_MODEL = env.embeddings_model
OPENAI_API_KEY = env.openai_api_key

router = APIRouter()


@router.post("/ingest_url_content", response_model=IngestResponse)
def ingest(req: IngestRequest) -> IngestResponse:
    """
    Endpoint for ingesting content from URLs into Weaviate.

    This endpoint accepts a list of URLs, extracts the content of each page,
    generates embeddings using the configured model, and stores the data
    into the specified Weaviate index.

    Args:
        req (IngestRequest): Object containing the list of URLs to be processed.

    Raises:
        HTTPException: If no URL is provided (status code 400).

    Returns:
        IngestResponse: Object containing:
            - collection (str): Name of the collection/index in Weaviate.
            - results (List[IngestResult]): Individual ingestion results,
              including status, error messages, and number of processed chunks.
            - total_chunks (int): Total number of successfully processed chunks.
    """
    logger.info(f"Received ingestion request with {len(req.urls)} URLs")

    if not req.urls:
        raise HTTPException(status_code=400, detail="Please, send at least one URL...")

    # Ingestion
    raw_results = ingest_urls_to_weaviate(
        urls=[str(u) for u in req.urls],
        index_name=INDEX_NAME,
        openai_api_key=OPENAI_API_KEY,
        embeddings_model=EMBEDDINGS_MODEL,
    )

    # Results parsing
    results = [IngestResult(**r) for r in raw_results]
    total_chunks = sum(r.chunks for r in results if r.ok)

    return IngestResponse(collection=INDEX_NAME, results=results, total_chunks=total_chunks)
