from fastapi import HTTPException, APIRouter
from dotenv import load_dotenv
from utils.logger_utils import setup_logger
from services.ingest_data import ingest_urls_to_weaviate
from api.schemas.ingest_data_schema import IngestRequest, IngestResponse, IngestResult
import os

logger = setup_logger(__name__)
load_dotenv()

INDEX_NAME = os.getenv("INDEX_NAME", "rag_web_data")
EMBEDDINGS_MODEL = os.getenv("EMBEDDINGS_MODEL", "text-embedding-3-small")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found. Verify if the environment variable is defined!")

router = APIRouter()

@router.post("/ingest_url_content", response_model=IngestResponse)
def ingest(req: IngestRequest) -> IngestResponse:
    
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

    # Results parsing
    results = [IngestResult(**r) for r in raw_results]
    total_chunks = sum(r.chunks for r in results if r.ok)

    return IngestResponse(collection=INDEX_NAME, results=results, total_chunks=total_chunks)
