from typing import List
from fastapi import HTTPException, APIRouter
from pydantic import BaseModel, HttpUrl
from utils.logger_utils import setup_logger
from utils.ingest_data_utils import ingest_urls_to_weaviate

from dotenv import load_dotenv
import os

logger = setup_logger(__name__)
load_dotenv()

INDEX_NAME = os.getenv("INDEX_NAME", "rag_web_data")
EMBEDDINGS_MODEL = os.getenv("EMBEDDINGS_MODEL", "text-embedding-3-small")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found. Verify if the environment variable is defined!")

router = APIRouter()

# ------------ Schemas (permanecem na rota) ------------

class IngestRequest(BaseModel):
    urls: List[HttpUrl]

class IngestResult(BaseModel):
    url: HttpUrl
    ok: bool
    chunks: int
    error: str | None = None

class IngestResponse(BaseModel):
    collection: str
    results: List[IngestResult]
    total_chunks: int

# ------------ Route ------------

@router.post("/ingest_url_content", response_model=IngestResponse)
def ingest(req: IngestRequest) -> IngestResponse:

    """
    Ingests the content of one or more URLs into a Weaviate collection using OpenAI embeddings.

    This endpoint validates the provided URLs, extracts their content, and stores the
    chunked data in the configured Weaviate index. Each ingestion result includes
    the URL, ingestion status, number of chunks processed, and any errors encountered.

    Args:
        req (IngestRequest): A request body containing a list of valid URLs to ingest.

    Returns:
        IngestResponse: A response containing the collection name, ingestion results
        for each URL, and the total number of chunks successfully processed.

    Raises:
        HTTPException: If no URLs are provided in the request.
        ValueError: If the required `OPENAI_API_KEY` environment variable is not set.
    """
    
    logger.info(f"Received ingestion request with {len(req.urls)} URLs")

    # Urls validation
    if not req.urls:
        raise HTTPException(status_code=400, detail="Please, send at least one URL...")

    # Ingestion
    raw_results = ingest_urls_to_weaviate(
        urls=[str(u) for u in req.urls],
        index_name=INDEX_NAME,
        openai_api_key=OPENAI_API_KEY,
        embeddings_model=EMBEDDINGS_MODEL,
    )

    # Results
    results = [IngestResult(**r) for r in raw_results]
    total_chunks = sum(r.chunks for r in results if r.ok)

    return IngestResponse(collection=INDEX_NAME, results=results, total_chunks=total_chunks)
