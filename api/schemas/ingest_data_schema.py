from typing import List, Optional
from pydantic import BaseModel, HttpUrl

# -------------------------------------------------
# Schemas for request and response models
# of the ingestion endpoint for Weaviate
# -------------------------------------------------

class IngestRequest(BaseModel):
    """
    Represents the request body for URL ingestion.

    Attributes:
        urls (List[HttpUrl]): A list of valid URLs to be processed and ingested.
    """
    urls: List[HttpUrl]

class IngestResult(BaseModel):
    """
    Represents the result of processing a single URL.

    Attributes:
        url (HttpUrl): The URL that was processed.
        ok (bool): Indicates whether ingestion succeeded or failed.
        chunks (int): Number of text chunks extracted and stored.
        error (Optional[str]): Error message if ingestion failed, otherwise None.
    """
    url: HttpUrl
    ok: bool
    chunks: int
    error: Optional[str] = None


class IngestResponse(BaseModel):
    """
    Represents the overall ingestion response.

    Attributes:
        collection (str): Name of the Weaviate collection/index where the data was stored.
        results (List[IngestResult]): List of ingestion results for each URL.
        total_chunks (int): Total number of successfully ingested chunks across all URLs.
    """
    collection: str
    results: List[IngestResult]
    total_chunks: int
